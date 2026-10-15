
QUIC PADDING Fingerprinting Lab
-------------------------------

The lab measures whether QUIC PADDING strategies erase the packet-size signal a traffic classifier relies on.

Rebuilding
----------

On a newly installed Ubuntu 24.04 machine:

    rm -rf /tmp/quic-fp-repro && mkdir /tmp/quic-fp-repro && cd /tmp/quic-fp-repro
    wget https://github.com/ngomahuru/quic-fp/releases/download/v1.1/quic-fp-1.1.tar.gz
    wget https://github.com/ngomahuru/quic-fp/releases/download/v1.1/quic-fp-1.1.sha256
    if sha256sum -c quic-fp-1.1.sha256; then
      tar xzf quic-fp-1.1.tar.gz && cd quic-fp-1.1 && ./scripts/rebuild.sh
    else
      echo "STOP: The archive does not match the published checksum"
    fi

An OK message is printed when the archive matches its published checksum, and the rebuild only starts after a match. For an independent check, compare the checksum inside quic-fp-1.1.sha256 with the one printed in the dissertation appendix.

The script prints what the study does, checks its prerequisites and asks once before installation. It then verifies the included dataset against its checksum, rebuilds the tables and figures, reruns the robustness sweep and compares eleven rebuilt tables against the originals. The script stops on any system other than Ubuntu 24.04.

Everything it produces goes into the folders `venv/`, `rebuild/` and `output/`, plus one working copy at `features/dataset.csv`. Remove all of them with command:

    rm -rf rebuild output venv features/dataset.csv

The SHA256 checksum of the archive is published with the v1.1 release on GitHub and in the dissertation appendix.

What is included in the Package
-------------------------------

The paths in the package and what they contain:

- `aioquic-fork/` : The modified QUIC library, complete and readable, BSD-licensed
- `scripts/` : The rebuild script, collection drivers, figures, fork patches
- `analysis/` : Evaluator, statistics, size-reliance measures, robustness sweep, pinned requirements
- `features/` : The feature extractor, and the working copy of the dataset written during rebuild
- `runs/` : The dataset, tables, and figures
- `runs_collect_1.log` : Collection log, one line per captured flow
- `LICENSE` : The MIT licence covering the project's own code, permissive with attribution

Reading the Verdict
-------------------

The script ends with eleven lines reading MATCH or DIFFERS, one per table, then a summary. The eleven tables are:

- `f1_summary.csv`, `f1_by_seed.csv`, `comparison.csv` and `pairwise.csv` : weighted F1 and the significance tests
- `dropcol.csv` : reliance on packet size
- `perclass_f1.csv` : F1 for each class
- `robustness.csv` : weighted F1 under three model variations
- `confusion_none_counts.csv`, `confusion_fixed_counts.csv`, `confusion_random_counts.csv` and `confusion_mtu_counts.csv` : the averaged confusion counts behind the four confusion matrices

Every table should match within a tolerance of one part in a billion, because the analysis is deterministic, the same data, the same fixed seeds in `scripts/seeds.txt`, and the same library versions in `analysis/requirements.txt`.

A DIFFERS line means a number moved beyond floating-point noise. Normally, this is caused by a library version resolving differently from the pinned file.

Figures are not compared automatically since Matplotlib renders fonts and writes metadata in ways varying between versions and platforms, so two visually similar figures can differ byte for byte. The script lists each pair of paths at the end. Open them side by side and compare. The confusion counts behind the four confusion matrices are compared in the verdict, so a MATCH there confirms the numbers each matrix draws.

Reading the Tables
------------------

Each table is printed with a title and a one-line description. In the pairwise table, a negative gap means the first strategy named removed less weighted F1 than the second, since the comparison subtracts the first from the second.

What cannot be rebuilt
----------------------

The residual table, `runs/run_1/residual_above_target.csv`, and the Phase 8 packet sizes, `runs/phase8_sizes.csv`. Both are measured from the raw captures, which are not included.

The Wireshark screenshots in `runs/run_1_figures/`. They show a decrypted PADDING frame in the same packet as a real HTTP/3 response, which needs both the encrypted packet payloads and the TLS session keys. Neither is included, the captures are large and regenerable, and key material is kept out of the repository as a matter of practice, whatever it protects.

Producing equivalent screenshots requires fresh data collection, which took 94 minutes for this run and requires several software packages. That is outside what this reproducibility package supports. The full procedure for new data collection and screenshot production is in Appendix A of the dissertation.

Library Changes
---------------

The modified QUIC library ships in full under `aioquic-fork/`. The three edited files are `configuration.py`, `connection.py` and `packet_builder.py` under `src/aioquic/quic/`, and `scripts/aioquic_padding.patch` shows the 28 added lines as a plain diff. `scripts/aioquic_upstream_commit.txt` names the upstream commit they apply to.

Scope of Reproduction
---------------------

The package reproduces one collection. The intervals describe split-to-split variation and not variation between collections. The included dataset reproduces every reported number. Recollecting data is a different activity and will not reproduce these numbers. The recollection needs Docker, the built images, packet-capture permissions and about 94 minutes, and it generates new traffic. The client draws every request size, and the random padding strategy every padding length, from Python's default generator, which is not seeded, and packet timing varies from run to run, so no two collections produce the same captures and the figures differ.

Version History
---------------

- v1.1 : Adds the robustness table and the four confusion-count tables to the reproduction verdict, so the rebuild compares eleven tables. The printed captions and the robustness messages now name weighted F1 for the overall score and F1 for one class, in place of accuracy. The dataset, every calculation and every archived table are unchanged from v1.0.
- v1.0 : First release. The rebuild compares six tables.

Licence
-------

The project's own code is under the Massachusetts Institute of Technology (MIT) licence, which allows anyone to use, change and redistribute it, including commercially, provided the copyright notice travels with it. The full text is in `LICENSE`.

`aioquic-fork/` is a modified copy of aioquic and remains under its original BSD licence, in `aioquic-fork/LICENSE`.
