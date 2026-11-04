#!/usr/bin/env python3
"""Portable exact checks for unequal-circle .pck files in the centred unit square.

Standard library only. File layout: maximum radius, author, then x y r triples
sorted by increasing radius. Every decimal is interpreted as an exact rational.
Contact counts use a strict 3e-12 distance-gap threshold; they are not feasibility
tolerances. Exact feasibility, contact-count eligibility and attribution are
reported independently. No optimality or Lean-kernel claim is made.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time

CONTACT_TOLERANCE = Fraction(3, 10**12)
PLACEHOLDER = "AUTHOR NAME REQUIRED"
VERSION = "public-pck-csv-verifier/v2"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decimal24(value):
    value = Fraction(value)
    scaled = value * 10**24
    require(scaled.denominator == 1, "Value has no lossless 24-place decimal representation")
    integer = scaled.numerator
    sign = "-" if integer < 0 else ""
    whole, part = divmod(abs(integer), 10**24)
    text = f"{sign}{whole}.{part:024d}"
    require(Fraction(text) == value, "Decimal round-trip failed")
    return text


def decimal_token(token):
    require(re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", token) is not None,
            "Expected finite decimal token")
    return Fraction(token)


def filename_count(path):
    match = re.fullmatch(r'(?:N0*|csqv0*)([1-9][0-9]*)\.pck', Path(path).name)
    return int(match.group(1)) if match else None


def read_pck(path, expected_n=None):
    raw = Path(path).read_bytes()
    lines = raw.decode("utf-8").splitlines()
    require(len(lines) >= 3, "Missing header, author or circle rows")
    require(len(lines[0].split()) == 1, "Maximum-radius header must contain one decimal")
    maximum = decimal_token(lines[0].strip())
    author = lines[1].strip()
    require(author and "\x00" not in author, "Missing or invalid author")
    circles = []
    for index, line in enumerate(lines[2:], 1):
        tokens = line.split()
        require(len(tokens) == 3, f"Circle row {index} must contain exactly x y r")
        circles.append(tuple(decimal_token(token) for token in tokens))
    if expected_n is not None:
        require(type(expected_n) is int and expected_n > 0, "Invalid expected count")
        require(len(circles) == expected_n, "Circle count differs from expected count")
    named_n = filename_count(path)
    if named_n is not None:
        require(len(circles) == named_n, "Circle count differs from filename N")
    require(circles and maximum == max(r for _, _, r in circles), "Maximum-radius header mismatch")
    require(all(circles[i][2] <= circles[i+1][2] for i in range(len(circles)-1)),
            "Radii are not sorted in increasing order")
    return circles, author, maximum, hashlib.sha256(raw).hexdigest()


def verify_geometry(circles, *, tolerance=CONTACT_TOLERANCE):
    """Exact near-pair checks plus an integer separation proof for every far pair."""
    require(circles and tolerance > 0, "Empty geometry or invalid contact threshold")
    denominator = math.lcm(2, tolerance.denominator,
                           *(v.denominator for circle in circles for v in circle))
    half = denominator // 2
    threshold = int(tolerance * denominator)
    z = [tuple(int(v * denominator) for v in circle) for circle in circles]
    wall_contacts = 0
    for i, (x, y, r) in enumerate(z):
        require(r > 0, f"Nonpositive radius at circle {i+1}")
        slacks = (half+x-r, half-x-r, half+y-r, half-y-r)
        require(min(slacks) >= 0, f"Circle {i+1} crosses a square wall")
        wall_contacts += sum(gap < threshold for gap in slacks)
    width = 2 * max(r for _, _, r in z) + threshold
    buckets = defaultdict(list)
    checked = pair_contacts = 0
    for i, (x, y, r) in enumerate(z):
        a, b = x // width, y // width
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                for j in buckets.get((a+da, b+db), ()):
                    xx, yy, rr = z[j]
                    distance2 = (x-xx)**2 + (y-yy)**2
                    radius_sum = r+rr
                    require(distance2 >= radius_sum**2, f"Overlapping circles {j+1},{i+1}")
                    pair_contacts += distance2 < (radius_sum+threshold)**2
                    checked += 1
        buckets[(a, b)].append(i)
    occupancy = Counter((x//width, y//width) for x, y, _ in z)
    independent_neighbours = sum(c*(c-1)//2 for c in occupancy.values())
    for (a, b), count in occupancy.items():
        for da, db in ((0, 1), (1, -1), (1, 0), (1, 1)):
            independent_neighbours += count*occupancy.get((a+da, b+db), 0)
    n = len(z)
    total = n*(n-1)//2
    require(checked == independent_neighbours and 0 <= checked <= total, "Pair partition mismatch")
    contacts = pair_contacts + wall_contacts
    return dict(status="PASS", n=n, score_exact=str(sum((r for _, _, r in circles), Fraction())),
                max_radius_exact=str(max(r for _, _, r in circles)),
                positive_radius_checks=n, wall_inequalities=4*n,
                all_pair_obligations=total, evaluated_pairs=checked,
                separated_pairs=total-checked, integer_denominator=str(denominator),
                bucket_width_integer=str(width), occupied_buckets=len(buckets),
                far_pair_proof="An omitted pair has a bucket-index difference at least 2 on one axis. Integer axis separation is at least width+1, where width=2*max_radius+contact_threshold. Thus it is strictly separated, and its distance gap exceeds the contact threshold.",
                contact_tolerance_exact=str(tolerance), contact_comparison="strict gap < tolerance",
                circle_contacts=pair_contacts, wall_contacts=wall_contacts, total_contacts=contacts,
                contact_gate_required=3*n, contact_gate="PASS" if contacts >= 3*n else "FAIL",
                scope="Exact external feasibility of these serialized coordinates; contact hint gate separately reported; no optimality or Lean-kernel claim.")


def verify_file(path, *, expected_n=None, expected_score=None, expected_sha256=None,
                geometry_path=None, expected_geometry_sha256=None, expected_author=None):
    circles, author, maximum, digest = read_pck(path, expected_n)
    if expected_sha256 is not None:
        require(digest == expected_sha256, "Serialized file SHA256 mismatch")
    if expected_author is not None:
        require(author == expected_author, "Author header differs from manifest")
    result = verify_geometry(circles)
    if expected_score is not None:
        require(Fraction(result['score_exact']) == Fraction(expected_score), "Exact radius sum mismatch")
    if geometry_path is not None:
        if expected_geometry_sha256 is not None:
            require(sha(geometry_path) == expected_geometry_sha256, "Portable geometry SHA256 mismatch")
        document = json.loads(Path(geometry_path).read_text())
        require(type(document['n']) is int and document['n'] == len(circles), "Portable geometry count mismatch")
        raw = document['circles']
        require(all(isinstance(row, list) and len(row) == 3 and all(type(v) in (str, int) for v in row) for row in raw),
                "Portable geometry must contain exact rational triples")
        original = [tuple(Fraction(v) for v in row) for row in raw]
        transformed = sorted(((x-Fraction(1,2), y-Fraction(1,2), r) for x, y, r in original), key=lambda c:c[2])
        require(circles == transformed, "Serialized geometry differs from source after centering and stable radius sort")
        require(Fraction(document['score_exact']) == Fraction(result['score_exact']), "Portable geometry score mismatch")
    return dict(result, pck_sha256=digest, author=author,
                author_status="unresolved" if author == PLACEHOLDER else "provided_not_independently_attributed",
                verifier_version=VERSION)



def main(argv=None):
    parser = argparse.ArgumentParser(description="Check stored circle coordinates exactly; no optimization is performed.")
    parser.add_argument('file', nargs='?', type=Path)
    parser.add_argument('--all', action='store_true', help='Check all packings against data/RESULTS.csv')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--report', type=Path, help='Optional JSON report with every file and measured runtime')
    args = parser.parse_args(argv)
    start = time.perf_counter()
    outputs = []
    try:
        require(args.all != bool(args.file), 'Specify one .pck file or --all')
        if args.all:
            root = args.root.resolve()
            with (root/'data/RESULTS.csv').open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            require(rows and len(rows) == len({int(r['N']) for r in rows}), 'Empty score table or duplicate N')
            expected = set()
            for row in rows:
                name = row['packing_file']; n = int(row['N'])
                require(Path(name).name == name and name == f'csqv{n}.pck', 'Invalid packing filename')
                expected.add(name)
            require({p.name for p in (root/'packings').glob('*.pck')} == expected, 'Packing set differs from score table')
            jobs = [(root/'packings'/r['packing_file'], int(r['N']), r['radius_sum_exact']) for r in rows]
        else:
            jobs = [(args.file, filename_count(args.file), None)]
        for path, n, score in jobs:
            file_start = time.perf_counter()
            try:
                result = verify_file(path, expected_n=n, expected_score=score)
                result['file'] = path.name
                result['exact_sum_matches_csv'] = True if score is not None else None
                print(f"PASS {path.name} N={result['n']} sum_exact={result['score_exact']}", flush=True)
                if result['contact_gate'] != 'PASS':
                    print(f"CONTACT WARNING {path.name}: {result['total_contacts']} < {result['contact_gate_required']} at strict gap < 3e-12 (exact feasibility still passes)", flush=True)
            except (ValueError,KeyError,TypeError,OSError,UnicodeError,ZeroDivisionError) as error:
                result = dict(status='FAIL', file=path.name, n=n, reason=str(error))
                print(f"FAIL {path.name}: {error}", flush=True)
            result['wall_seconds'] = time.perf_counter()-file_start
            outputs.append(result)
        failed = [r['file'] for r in outputs if r['status'] != 'PASS']
        summary = dict(status='FAIL' if failed else 'PASS', verified=len(outputs)-len(failed), failures=failed,
                       contact_warnings=[r['n'] for r in outputs if r.get('contact_gate') == 'FAIL'],
                       exact_score_comparisons=sum(r.get('exact_sum_matches_csv') is True for r in outputs),
                       wall_seconds=time.perf_counter()-start, files=outputs,
                       scope='Exact feasibility and recorded sums; approximate contact counts separate; no optimality claim.')
        if args.report:
            args.report.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
        print(f"{summary['status']}: {summary['verified']}/{len(outputs)} files; {summary['exact_score_comparisons']} CSV sums checked; {summary['wall_seconds']:.3f} seconds.")
        return 1 if failed else 0
    except (ValueError,KeyError,TypeError,OSError,UnicodeError,ZeroDivisionError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
