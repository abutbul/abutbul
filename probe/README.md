# probe

T1 picture in summary:

<details>
<summary><picture><img src="bar1.svg" width="760" alt="A"></picture></summary>

T1 body

</details>

T2 plain img in summary:

<details>
<summary><img src="bar1.svg" width="760" alt="B"></summary>

T2 body

</details>

T3 stacked linked images align=top:

<p><a href="https://github.com/abutbul/trbbs"><img align="top" src="bar1.svg" width="100%" alt="x"></a>
<a href="#probe"><img align="top" src="bar2.svg" width="100%" alt="y"></a>
<a href="#probe"><img align="top" src="bar1.svg" width="100%" alt="z"></a></p>

T4 stacked linked images, no align:

<p><a href="https://github.com/abutbul/trbbs"><img src="bar1.svg" width="100%" alt="x"></a>
<a href="#probe"><img src="bar2.svg" width="100%" alt="y"></a></p>

T5 stacked picture images with br:

<picture><img src="bar1.svg" width="100%" alt="x"></picture><br><picture><img src="bar2.svg" width="100%" alt="y"></picture>

T6 details name group:

<details name="menu"><summary>one</summary>body one</details>
<details name="menu"><summary>two</summary>body two</details>

T7 kbd: <kbd>A</kbd> About

T8 summary with picture full width, details inside p-less stack:

<details><summary><picture><img align="top" src="bar1.svg" width="100%" alt="A"></picture></summary><picture><img align="top" src="bar2.svg" width="100%" alt="body"></picture></details>
<details><summary><picture><img align="top" src="bar2.svg" width="100%" alt="A"></picture></summary><picture><img align="top" src="bar1.svg" width="100%" alt="body"></picture></details>
