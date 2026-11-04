# Circles in a Square

**Audrey Hillenbrand**  
University of Chicago Laboratory Schools High School

I study how to arrange circles of different sizes inside a square so that they do not overlap and the sum of their radii is as large as possible. This repository presents 326 packing results from that research.

## The problem

For a fixed number of circles, $N$, the objective is to maximize

$$
S_N = \sum_{i=1}^{N} r_i,
$$

where $r_i$ is the radius of circle $i$. Every circle must fit inside the unit square, and no two circles may overlap.

This differs from maximizing the area covered by the circles. A useful change can make some circles smaller while enlarging others by a greater total amount. Because the circles constrain one another, an improvement in one part of the square may require adjustments elsewhere. Many arrangements resist further improvement even when a better arrangement exists.

![Circle packings for N112, N314 and N1024](assets/packing_examples.svg)

## My research

I use a repeated cycle of **research → hypothesis → test → analysis → revision**. I study the problem, identify questions, design comparisons, assess the results, and use what I learn to guide the next experiments.

I use Astra, an OpenAI ChatGPT model, to help implement and run tests and analyze their outcomes. My role is to direct the research, evaluate the evidence, and decide which ideas to pursue. Some experiments build on previously published packings.

One important lesson is that improving a starting arrangement does not necessarily improve the best known result. I distinguish gains over an experiment's starting point from gains over my retained results and the published benchmark.

## How the generator works

The generator is a program that creates candidate arrangements and searches for improvements. I developed it through repeated experiments comparing different starting geometries and ways of moving the circles. It has five main parts:

1. **Construct starting arrangements.** Create rows, triangular patterns and boundary arrangements with different orientations and offsets. This provides several starting points, including for circle counts without an existing packing.
2. **Adapt nearby packings.** Use an arrangement with slightly fewer or more circles as a starting point. Add or remove circles, or split a circle or merge a pair. Selected older arrangements remain useful even after their own scores have been surpassed.
3. **Optimize the whole packing.** Adjust circle centers and radii together. Some circles may shrink while others grow by a greater total amount. Exploratory routes can temporarily lose score while the best saved packing remains available.
4. **Explore contacts and finish.** Change selected touching relationships to allow new movements, then refine promising arrangements. Continue productive searches while keeping unsuccessful alternatives from replacing a better result.
5. **Keep improvements and feed them back.** Check candidate packings, retain the best scores, and use useful new geometries as starting points for other counts. Records of completed experiments help avoid repeating identical work.

Different circle counts benefit from different arrangements and search routes. The generator combines these parts to explore several possibilities and retain the strongest result found.

## Results

The comparisons use Packomania's table downloaded on **November 1, 2026**.

| Category | Number of circle counts |
|---|---:|
| Scores exceeding the website by more than 0.000001 | 287 |
| Counts absent from that website snapshot | 39 |
| Total included | 326 |

The 0.000001 threshold is my reporting cutoff, not a stated Packomania acceptance rule. These are computational results, not proofs of global optimality. The 39 unlisted counts are potential additions to the website, rather than claims that those counts have never been studied.

The largest absolute leads in this release are:

| N | Radius sum, rounded | Website sum | Difference, rounded |
|---:|---:|---:|---:|
| 7396 | 46.091252476015 | 46.035967997707 | +0.055284478308 |
| 9801 | 53.068829058133 | 53.015624816539 | +0.053204241594 |
| 5041 | 38.022949097220 | 37.975219102505 | +0.047729994715 |
| 1024 | 17.084471242609 | 17.059358817280 | +0.025112425329 |
| 7744 | 47.154533578632 | 47.130009798205 | +0.024523780427 |

The GitHub release and accompanying Packomania submission contain the same 326 packing files.
