# accumulation_agent

**Stack:** python
**Tree Hash:** 7b6c4235cab8f4de7cf3668f1d47607927b5c3f8c8ca6cf9ce77ba9ae8537071

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
│   │   ├── 04cfd165300e2567
│   │   ├── 06ff41b28dd7b0cd
│   │   ├── 07cf5908620ab55e
│   │   ├── 13c8ba7511fd1a03
│   │   ├── 2197d256db692b13
│   │   ├── 2442fdd4ae7229fe
│   │   ├── 2d5b6343d12d6c78
│   │   ├── 2e478581159894c2
│   │   ├── 334b4921c0c0cc9b
│   │   ├── 343bb0c7c230e057
│   │   ├── 3fb5530f57f080ea
│   │   ├── 4be60c0b98d5ce77
│   │   ├── 563eb276cd68d4a5
│   │   ├── 5a6d6c39a990c3da
│   │   ├── 61b2d76eed7e683c
│   │   ├── 638d559f7143bb67
│   │   ├── 6b6ac5dca511f45f
│   │   ├── 6c5c0d066b189c15
│   │   ├── 716e9758f7a0e20e
│   │   ├── 71d919bb74aa005a
│   │   ├── 7360eb993cd343ff
│   │   ├── 780b0f72b801fe14
│   │   ├── 7e47b12f355c1c4a
│   │   ├── 7e9ad6eec462464d
│   │   ├── 8a7811de787aa965
│   │   ├── 8ba5f3d4a07921b8
│   │   ├── 92d2375c986411ed
│   │   ├── 92e336dcd3d74498
│   │   ├── 9dc75ff7a683e0a0
│   │   ├── 9f85e3c7615de6d1
│   │   ├── a862d5428b9a59d3
│   │   ├── aad1dcffcab48960
│   │   ├── bf43c8252c9c7a56
│   │   ├── c088aec815b2ed8b
│   │   ├── c11e6caa7f91f3e7
│   │   ├── c9492d17dbee22d5
│   │   ├── ce7b58072cd99e44
│   │   ├── d5e04402b3ebfb71
│   │   ├── d678c8069f1cd0ca
│   │   ├── d7003a2f3678affb
│   │   ├── da39a3ee5e6b4b0d
│   │   ├── de2bcacfdcb24a2d
│   │   ├── eb141cccf9ecf44d
│   │   ├── efdc023bb9ec74ef
│   │   ├── effe468330d424fd
│   │   ├── f0a6177e0be1978f
│   │   ├── f1f94b5325188df2
│   │   ├── f3d67a475dc95f23
│   │   └── f3d7bdabbd5c0b5e
│   ├── examples
│   └── .gitignore
├── .pytest_cache
│   ├── v
│   │   └── cache
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   └── README.md
├── .ruff_cache
│   ├── 0.15.14
│   │   ├── 14394155972235992549
│   │   └── 16524778214016307427
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
├── config
│   └── production.json
├── src
│   ├── abas.egg-info
│   │   ├── dependency_links.txt
│   │   ├── PKG-INFO
│   │   ├── requires.txt
│   │   ├── SOURCES.txt
│   │   └── top_level.txt
│   ├── backtest
│   │   ├── __init__.py
│   │   └── harness.py
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
│   │   └── orchestrator.py
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
│   │   └── tracker.py
│   ├── regime
│   │   └── __init__.py
│   ├── risk
│   │   ├── __init__.py
│   │   └── overlay.py
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
│   ├── test_backtest.py
│   ├── test_config.py
│   ├── test_custody.py
│   ├── test_data.py
│   ├── test_features.py
│   ├── test_grid.py
│   ├── test_inventory.py
│   ├── test_monitoring.py
│   ├── test_orchestrator.py
│   ├── test_portfolio.py
│   └── test_risk.py
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
├── pyproject.toml
├── README.md
└── TASK.md
```

## Build Commands

- Install: `pip install -e .`
- Test: `pytest`
- Lint: `ruff check .`
