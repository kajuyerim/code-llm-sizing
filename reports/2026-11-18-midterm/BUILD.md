# Midterm report build and template source

This source follows the nine chapter structure in the supplied CMPE 492 `report-template-v2.tex` and uses its `\title`, `\author`, `\date`, and `\maketitle` approach. The project title, student names, advisor, and Midterm Report identifier are retained. The report uses the official FBE style files in `styles/`; project packages and macros remain in `preamble.tex`.

## Build

Run from this directory with Tectonic installed:

```sh
build_dir="$(mktemp -d)"
tectonic --untrusted --outdir "$build_dir" main.tex
# After review, copy only the final PDF into the report directory.
cp "$build_dir/main.pdf" context-ops-midterm.pdf
```

The build directory is external and disposable. Tectonic 0.17.0 is the verified build version for this report. Do not add generated TeX auxiliaries, bibliography outputs, or caches to version control. Tectonic resolves the bibliography from `references.bib` with `styles/fbe_tez_v11.bst`.

## Template source and license

The supplied `report-template-v2.tex` is the project’s CMPE 492 structure reference. Its contents were preserved as nine report chapters, followed by the existing appendices. The report format is based on the official Bogazici University Institute of Graduate Studies in Science and Engineering thesis template, [available from the university template archive](https://mediastore.cc.bogazici.edu.tr/web/userfiles/files/fbe_adv_thesis_template_2022_2.zip), distributed locally as `fbe-template.zip`, SHA-256 `151418be852ac49b6d40571459f61a487c503a91d282a3d795f862726d7d36cd`.

`styles/fbe_tez.sty` and `styles/fbe_tez_v11.bst` are copied unchanged from that ZIP. The style credits Feza Kerestecioğlu and Mehmet Can Güven and permits distribution of unchanged copies when documentation is included. The bibliography style carries its upstream custom-bib and LaTeX Project Public License notices. This file documents the source and the relevant redistribution terms; the upstream ZIP's `README.txt` is empty. The files are retained byte-for-byte, including their license and attribution headers.

The document follows the supplied template and style files for this midterm report. This does not assert institutional approval or certify that the report satisfies every university submission requirement.

## Sources

The FBE style package's own headers identify its authors and redistribution conditions. Its companion bibliography style identifies the custom-bib source and includes the LaTeX Project Public License notice. Refer to those unchanged headers as the authoritative license text. The supplied archive and its checksum above identify the exact upstream files used.
