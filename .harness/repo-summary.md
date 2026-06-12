# accumulation_agent

**Stack:** python
**Tree Hash:** 44e6fec1947a9112df4ba8e202d48cf2dd473cdfc658ead27b88df9943754577

## Directory Structure

```
accumulation_agent
├── .github
│   └── workflows
│       └── ci.yml
├── .harness
│   ├── config.yaml
│   ├── feature_list.json
│   ├── progress.md
│   ├── repo-summary.md
│   ├── repo-summary.meta.json
│   ├── scope.yaml
│   └── verify.yaml
├── .hypothesis
│   ├── constants
│   │   ├── 00046c9965b4dcbf
│   │   ├── 02ceb9e0da566ab3
│   │   ├── 04cfd165300e2567
│   │   ├── 06ff41b28dd7b0cd
│   │   ├── 07cf5908620ab55e
│   │   ├── 0a8ca16dde7751d8
│   │   ├── 0b03068dcafb228a
│   │   ├── 112b1e383a59318c
│   │   ├── 1212b174d721965e
│   │   ├── 13c8ba7511fd1a03
│   │   ├── 159a6bdf29236478
│   │   ├── 189da501ed0b1997
│   │   ├── 1adf4f690529eb5f
│   │   ├── 1c049971406ad615
│   │   ├── 2197d256db692b13
│   │   ├── 2442fdd4ae7229fe
│   │   ├── 2658833db9d488c5
│   │   ├── 2b2978f2cd00070d
│   │   ├── 2d5b6343d12d6c78
│   │   ├── 2ded159930e77934
│   │   ├── 2e478581159894c2
│   │   ├── 2e83e595328b5f3c
│   │   ├── 334b4921c0c0cc9b
│   │   ├── 343bb0c7c230e057
│   │   ├── 346fc63bce2f6f1a
│   │   ├── 349e213761ac8609
│   │   ├── 38bc094b96847163
│   │   ├── 397c38c04fcf8873
│   │   ├── 3fb5530f57f080ea
│   │   ├── 42698aeb6588f137
│   │   ├── 48e57db20a2b5ae2
│   │   ├── 4be60c0b98d5ce77
│   │   ├── 563eb276cd68d4a5
│   │   ├── 5a6d6c39a990c3da
│   │   ├── 60c393f33f5e2697
│   │   ├── 61b2d76eed7e683c
│   │   ├── 638d559f7143bb67
│   │   ├── 63b5002cad280a8a
│   │   ├── 68db5467bf81072a
│   │   ├── 6b6ac5dca511f45f
│   │   ├── 6c5c0d066b189c15
│   │   ├── 6f76b48033d6ac82
│   │   ├── 716e9758f7a0e20e
│   │   ├── 717184aee170b21a
│   │   ├── 71d919bb74aa005a
│   │   ├── 7360eb993cd343ff
│   │   ├── 74a6d81396c304ac
│   │   ├── 75aab6d05dc1c1dc
│   │   ├── 780b0f72b801fe14
│   │   ├── 784d44fd270295e2
│   │   ├── 7e47b12f355c1c4a
│   │   ├── 7e9ad6eec462464d
│   │   ├── 7f307b933c20647f
│   │   ├── 84b90122bc4e286b
│   │   ├── 89c54e22ae499e4e
│   │   ├── 8a7811de787aa965
│   │   ├── 8b3092d1764a3061
│   │   ├── 8ba5f3d4a07921b8
│   │   ├── 92d2375c986411ed
│   │   ├── 92e336dcd3d74498
│   │   ├── 92f0d845fa2ac471
│   │   ├── 9394ec81560a6b3d
│   │   ├── 9b0b4836d5d9e88d
│   │   ├── 9dc75ff7a683e0a0
│   │   ├── 9f85e3c7615de6d1
│   │   ├── a58b7294e7314fec
│   │   ├── a862d5428b9a59d3
│   │   ├── a94ff25377fe52c2
│   │   ├── aa8cd9607066f13b
│   │   ├── aad1dcffcab48960
│   │   ├── af98643484d46ea8
│   │   ├── b2632528fa3669ff
│   │   ├── b79b9bb58714663f
│   │   ├── bab910a765a4faa4
│   │   ├── bf43c8252c9c7a56
│   │   ├── c088aec815b2ed8b
│   │   ├── c11e6caa7f91f3e7
│   │   ├── c4e69c4a07062010
│   │   ├── c9492d17dbee22d5
│   │   ├── ce7b58072cd99e44
│   │   ├── d4c53c1f5bead781
│   │   ├── d5e04402b3ebfb71
│   │   ├── d678c8069f1cd0ca
│   │   ├── d7003a2f3678affb
│   │   ├── d7f2e09bb98e4197
│   │   ├── da39a3ee5e6b4b0d
│   │   ├── dad32b6f44779f5b
│   │   ├── de2bcacfdcb24a2d
│   │   ├── df33819e17e2099b
│   │   ├── e3d64a9e63347ad7
│   │   ├── eb141cccf9ecf44d
│   │   ├── efdc023bb9ec74ef
│   │   ├── effe468330d424fd
│   │   ├── f0a6177e0be1978f
│   │   ├── f1f94b5325188df2
│   │   ├── f3d67a475dc95f23
│   │   ├── f3d7bdabbd5c0b5e
│   │   ├── f4495cdb01d8c8f4
│   │   ├── faac8937fb326456
│   │   └── fdc3c27bc057f808
│   ├── examples
│   │   ├── 04e6b3400353b141
│   │   ├── a6f304fd83dfc56a
│   │   └── bae1731f6f06ab0a
│   └── .gitignore
├── .pytest_cache
│   ├── v
│   │   └── cache
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   └── README.md
├── .ruff_cache
│   ├── 0.15.14
│   │   ├── 13475693904834168192
│   │   ├── 14394155972235992549
│   │   ├── 16524778214016307427
│   │   └── 3191274809267027698
│   ├── .gitignore
│   └── CACHEDIR.TAG
├── .venv
│   ├── Lib
│   │   └── site-packages
│   ├── Scripts
│   │   ├── activate
│   │   ├── activate_this.py
│   │   ├── activate.bat
│   │   ├── activate.csh
│   │   ├── activate.fish
│   │   ├── activate.nu
│   │   ├── activate.ps1
│   │   ├── deactivate.bat
│   │   ├── dotenv.exe
│   │   ├── f2py.exe
│   │   ├── hypothesis.exe
│   │   ├── idna.exe
│   │   ├── normalizer.exe
│   │   ├── numpy-config.exe
│   │   ├── py.test.exe
│   │   ├── pydoc.bat
│   │   ├── pygmentize.exe
│   │   ├── pytest.exe
│   │   ├── python.exe
│   │   ├── pythonw.exe
│   │   └── ruff.exe
│   ├── .gitignore
│   ├── .lock
│   ├── CACHEDIR.TAG
│   └── pyvenv.cfg
├── .vscode
│   └── settings.json
├── artifacts
│   └── backtest_report.md
├── config
│   └── production.json
├── data
│   └── btc_1h_binance.parquet
├── src
│   ├── abas.egg-info
│   │   ├── dependency_links.txt
│   │   ├── PKG-INFO
│   │   ├── requires.txt
│   │   ├── SOURCES.txt
│   │   └── top_level.txt
│   ├── ai
│   │   ├── env.py
│   │   ├── pbo.py
│   │   └── rl_agent.py
│   ├── backtest
│   │   ├── __init__.py
│   │   ├── benchmarks.py
│   │   ├── download_data.py
│   │   ├── harness.py
│   │   └── run_simulations.py
│   ├── custody
│   │   ├── __init__.py
│   │   └── sweeper.py
│   ├── data
│   │   ├── __init__.py
│   │   ├── ingester.py
│   │   └── validators.py
│   ├── execution
│   │   ├── __init__.py
│   │   ├── ccxt_mock.py
│   │   ├── delta_neutral.py
│   │   ├── live_ws.py
│   │   ├── orchestrator.py
│   │   └── paper.py
│   ├── features
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── grid
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── inventory
│   │   ├── __init__.py
│   │   ├── ledger.py
│   │   └── models.py
│   ├── monitoring
│   │   ├── __init__.py
│   │   └── exporter.py
│   ├── portfolio
│   │   ├── __init__.py
│   │   ├── reconcile_audit.py
│   │   └── tracker.py
│   ├── regime
│   │   ├── __init__.py
│   │   ├── bocpd.py
│   │   ├── classifier.py
│   │   ├── hmm.py
│   │   └── kmeans.py
│   ├── risk
│   │   ├── __init__.py
│   │   └── overlay.py
│   ├── simulator
│   │   └── market_sim.py
│   ├── utils
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── init_db.py
│   │   └── logging.py
│   ├── __init__.py
│   └── config.py
├── tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_audit.py
│   ├── test_backtest.py
│   ├── test_benchmarks.py
│   ├── test_config.py
│   ├── test_custody.py
│   ├── test_data.py
│   ├── test_delta_neutral.py
│   ├── test_download_data.py
│   ├── test_features.py
│   ├── test_grid.py
│   ├── test_inventory.py
│   ├── test_monitoring.py
│   ├── test_orchestrator.py
│   ├── test_paper.py
│   ├── test_portfolio.py
│   ├── test_regime.py
│   ├── test_risk.py
│   ├── test_rl.py
│   ├── test_run_simulations.py
│   └── test_simulator.py
├── .env
├── .gitignore
├── ABAS_PLAN_v2_VI.md
├── ABAS_PLAN_v2.md
├── AGENTS_CONFIG.md
├── AGENTS_CONVENTIONS.md
├── AGENTS_HARNESS.md
├── AGENTS_OLD.md
├── AGENTS_REPO.md
├── AGENTS_SAFETY.md
├── AGENTS_SPECS.md
├── AGENTS.md
├── CHANGELOG.md
├── docker-compose.yml
├── project_review.md
├── pyproject.toml
├── README.md
├── TASK.md
└── uv.lock
```

## Build Commands

- Install: `pip install -e .`
- Test: `pytest`
- Lint: `ruff check .`
