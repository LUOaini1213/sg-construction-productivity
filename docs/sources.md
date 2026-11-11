# Sources

All retrieval was done on 2026-11-11 (Singapore time). Raw files are in `data/raw/` with SHA-256 hashes in
`data/raw/manifest.json`; `scripts/fetch_data.py` repeats the download.

## Open datasets (committed, Singapore Open Data Licence v1.0)

Licence: https://data.gov.sg/open-data-licence. Attribution: "Contains information from the datasets below
accessed on 2026-11-11 from data.gov.sg, which is made available under the terms of the Singapore Open Data
Licence version 1.0."

| File | data.gov.sg dataset | Source table | Used |
|---|---|---|---|
| `va_per_worker_chained_annual.csv` | d_43c4c89b056bc3b3959e4cf6771c2898, "Value Added Per Worker In Chained (2015) Dollars, By Industry (SSIC 2020), Annual" (SingStat & MOM; last updated 2026-08-11) | SingStat M015761 | rows "Total (Based On GDP In Chained (2015) Dollars)" and "Construction" |
| `va_per_hour_chained_annual.csv` | d_c1fa91e0dd1a1960d5086a28ede16eea, "Value Added Per Actual Hour Worked In Chained (2015) Dollars By Industry, Annual" (SingStat & MOM; last updated 2026-08-11) | SingStat M015851 | rows "Total" and "Construction", 2009-2025 |
| `contracts_progress_annual.csv` | d_cfda05718261fe933db5e14c2ca2d432, "Contracts Awarded And Progress Payments Certified By Sector And Development Type, Annual" (source BCA; last updated 2026-10-08) | SingStat M400221, unit "Million Dollars" (read from the SingStat table API) | total, building work and civil engineering rows of the two "Total Public & Private Sector" blocks |
| `cmp_work_permit.csv` | d_4fb775d3cc311989261fae4ad22dde09, "Number of Foreign Domestic Workers and Construction, Marine, Process Work Permit Holders" (MOM; last updated 2024-06-06) | MOM | construction_marine_process rows, December 2017-2022 |

Dataset pages: `https://data.gov.sg/datasets/<dataset id>/view`. Download route: the data.gov.sg v1
`poll-download` API.

## BCA single figures (quoted with citation, not copied as tables)

Each figure, with the exact sentence location, is in `data/bca_figures.json`.

| Figure | URL | Where |
|---|---|---|
| DfMA adoption 31% (2019); 40% target for 2020 | https://www1.bca.gov.sg/resources/newsroom/good-progress-made-in-key-transformation-focus-areas-for-the-built-environment-sector-supported-by-a-skilled-and-competent-local-core/ | media release, 4 March 2020 |
| DfMA adoption 44% by GFA "today"; 70% by 2025 | https://www1.bca.gov.sg/resources/newsroom/built-environment-industry-transformation-map-to-facilitate-integration-and-collaborative-breakthrough-across-the-entire-value-chain/ | media release, 6 September 2022 |
| DfMA adoption about 61% (2023) and 68% (2024) by GFA; 70% target by 2025 | https://www1.bca.gov.sg/docs/default-source/docs-corp-news-and-publications/media-releases/bca-media-factsheet---mnd-cos-2025.pdf | MND COS 2025 media factsheets, Annex A, page 3, para 5. Read from the Wayback Machine snapshot `web.archive.org/web/20260208015325/` of this URL; the live URL returned 404 |
| PPVC: up to 40% manpower and time savings; up to 30% less time per floor; 1 to 2 months saved on average; case study up to 20% manpower | https://www1.bca.gov.sg/growth-and-transformation/productivity/design-for-manufacturing-and-assembly-dfma/prefabricated-prefinished-volumetric-construction-ppvc/ | BCA PPVC page, dated 1 October 2026 |
| Prefab MEP: time savings of up to 60% | https://www1.bca.gov.sg/growth-and-transformation/productivity/design-for-manufacturing-and-assembly-dfma/prefabricated-mechanical-electrical-and-plumbing-mep-system/ | BCA Prefab MEP page, dated 1 October 2026 |
| Mass engineered timber: up to 35% time savings | https://www1.bca.gov.sg/growth-and-transformation/productivity/design-for-manufacturing-and-assembly-dfma/mass-engineered-timber-met/ | BCA MET page, dated 16 March 2026 |

The 2019 and 2022 releases are read directly. BCA pages were read through an automated fetch that returned
the page text; figures were checked against the quoted sentences, not against screenshots.

## What I could not verify

- The data.gov.sg metadata API returns no per-dataset licence field. The Singapore Open Data Licence is the
  site licence; I did not find a dataset-level statement that confirms it for each of the four datasets.
- The live BCA COS 2025 factsheet URL returned 404; the 61%, 68% and 70% figures come from an archived copy.
- The reference year of the 44% figure: the September 2022 release says "today" without a year.
- Whether the four adoption figures use one definition. The 2019 figure does not say "by GFA" and may be on a
  different basis.
- A later BCA figure on whether the 70% target for 2025 was met. A secondary article mentioned 76%; I did not
  find it in a BCA source, so it is not used.
- Any construction-only foreign-worker series after 2022, and any open site productivity (m2 per man-day)
  series; neither was found on data.gov.sg.
- The project behind BCA's PPVC case-study figure, and how BCA's "up to" figures were measured.
- Every model parameter in `params/model.json`: these are assumptions, not sourced values.
