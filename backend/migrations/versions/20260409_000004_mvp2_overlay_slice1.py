"""mvp2 overlay slice 1 schema

Revision ID: 20260409_000004
Revises: 20260408_000003
Create Date: 2026-04-09 13:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_000004"
down_revision = "20260408_000003"
branch_labels = None
depends_on = None


PROXY_BASKETS = [
    (
        "private_equity_buyout",
        "asset_class:private_equity",
        "Private Equity Buyout",
        "private_equity",
        None,
        None,
        None,
        '["IWM", "SPY", "HYG"]',
        "[0.55, 0.25, 0.20]",
        1.3,
        "Broad US buyout proxy basket",
    ),
    (
        "venture_capital_growth",
        "asset_class:venture_capital",
        "Venture Capital Growth",
        "venture_capital",
        "technology",
        None,
        "micro_cap",
        '["QQQ", "SOXX", "ARKK"]',
        "[0.5, 0.25, 0.25]",
        1.5,
        "VC growth proxy basket",
    ),
    (
        "private_credit_direct_lending",
        "asset_class:private_credit",
        "Private Credit Direct Lending",
        "private_credit",
        "financials",
        None,
        None,
        '["BKLN", "HYG", "LQD"]',
        "[0.4, 0.35, 0.25]",
        1.2,
        "Direct lending proxy basket",
    ),
    (
        "real_estate_core",
        "asset_class:real_estate",
        "Real Estate Core",
        "real_estate",
        "real_assets",
        None,
        None,
        '["VNQ", "IYR", "XLRE"]',
        "[0.5, 0.25, 0.25]",
        1.3,
        "Core real estate proxy basket",
    ),
    (
        "infrastructure_energy",
        "asset_class:infrastructure",
        "Infrastructure Energy",
        "infrastructure",
        "energy",
        None,
        None,
        '["XLE", "AMLP", "BND"]',
        "[0.45, 0.35, 0.20]",
        1.1,
        "Energy infrastructure proxy basket",
    ),
    (
        "public_equity_core",
        "asset_class:public_equity",
        "Public Equity Core",
        "public_equity",
        None,
        None,
        "large_cap",
        '["SPY", "QQQ", "IWM"]',
        "[0.5, 0.3, 0.2]",
        1.0,
        "Core public equity basket",
    ),
    (
        "fixed_income_core",
        "asset_class:fixed_income",
        "Fixed Income Core",
        "fixed_income",
        None,
        None,
        None,
        '["AGG", "LQD", "IEF"]',
        "[0.45, 0.3, 0.25]",
        1.0,
        "Core fixed income basket",
    ),
    (
        "energy_renewables",
        "sector:energy",
        "Energy Renewables",
        "private_equity",
        "energy",
        None,
        None,
        '["XLE", "TAN", "FAN"]',
        "[0.35, 0.4, 0.25]",
        1.25,
        "Energy and renewables subsector basket",
    ),
]


STRESS_SCENARIOS = [
    ("gfc_2008", "2008 GFC", "Global credit seizure and equity collapse", "red", 10, '{"equity": -0.5, "credit_spread_bps": 500, "real_estate": -0.4}'),
    ("covid_2020", "COVID Crash", "Fast shock to growth and consumer demand", "red", 20, '{"equity": -0.35, "consumer": -0.6, "healthcare": 0.1}'),
    ("rate_shock_2022", "2022 Rate Shock", "Rates higher for longer with growth compression", "amber", 30, '{"ust10y_bps": 300, "technology": -0.5, "venture_capital": -0.6}'),
    ("renewables_policy_reversal", "Renewables Policy Reversal", "Policy rollback hits transition assets", "amber", 40, '{"renewables": -0.4, "infrastructure": -0.2}'),
    ("energy_price_collapse", "Energy Price Collapse", "Oil and gas demand shock", "amber", 50, '{"wti": -0.6, "energy": -0.45, "midstream": -0.25}'),
    ("em_contagion", "EM Contagion", "Broad EM selloff and FX drawdown", "amber", 60, '{"em_equity": -0.4, "em_fx": -0.25}'),
]


def upgrade() -> None:
    op.add_column("positions", sa.Column("factor_asset_class", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_sector", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_subsector", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_region", sa.Text(), nullable=True))
    op.add_column("positions", sa.Column("factor_market_segment", sa.Text(), nullable=True))

    op.create_table(
        "factor_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("factor_key", sa.Text(), nullable=False),
        sa.Column("factor_type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False),
        sa.Column("primary_driver", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sentiment_modifier", sa.Float(), nullable=False),
        sa.Column("signal_payload_json", sa.Text(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_factor_scores_workspace_id", "factor_scores", ["workspace_id"])
    op.create_index("ix_factor_scores_factor_key", "factor_scores", ["factor_key"])
    op.create_index("ix_factor_scores_as_of_date", "factor_scores", ["as_of_date"])

    op.create_table(
        "asset_factor_exposures",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id"), nullable=False),
        sa.Column("position_id", sa.String(length=36), sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("factor_key", sa.Text(), nullable=False),
        sa.Column("factor_type", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_asset_factor_exposures_workspace_id", "asset_factor_exposures", ["workspace_id"])
    op.create_index("ix_asset_factor_exposures_snapshot_id", "asset_factor_exposures", ["snapshot_id"])
    op.create_index("ix_asset_factor_exposures_position_id", "asset_factor_exposures", ["position_id"])
    op.create_index("ix_asset_factor_exposures_factor_key", "asset_factor_exposures", ["factor_key"])
    op.create_index("ix_asset_factor_exposures_as_of_date", "asset_factor_exposures", ["as_of_date"])

    op.create_table(
        "proxy_baskets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("basket_key", sa.Text(), nullable=False, unique=True),
        sa.Column("factor_key", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("asset_class", sa.Text(), nullable=False),
        sa.Column("sector", sa.Text()),
        sa.Column("region", sa.Text()),
        sa.Column("market_segment", sa.Text()),
        sa.Column("proxy_tickers_json", sa.Text(), nullable=False),
        sa.Column("proxy_weights_json", sa.Text(), nullable=False),
        sa.Column("illiquidity_scalar", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_proxy_baskets_factor_key", "proxy_baskets", ["factor_key"])

    op.create_table(
        "stress_scenarios",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("scenario_key", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("shock_json", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "risk_regimes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), sa.ForeignKey("portfolio_snapshots.id")),
        sa.Column("regime", sa.String(length=16), nullable=False),
        sa.Column("trigger_signal", sa.Text(), nullable=False),
        sa.Column("vix_level", sa.Float(), nullable=False),
        sa.Column("credit_spread_bps", sa.Float(), nullable=False),
        sa.Column("methodology_note", sa.Text(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_risk_regimes_workspace_id", "risk_regimes", ["workspace_id"])
    op.create_index("ix_risk_regimes_snapshot_id", "risk_regimes", ["snapshot_id"])
    op.create_index("ix_risk_regimes_as_of_date", "risk_regimes", ["as_of_date"])

    proxy_insert = sa.text(
        """
        INSERT INTO proxy_baskets
        (id, basket_key, factor_key, name, asset_class, sector, region, market_segment, proxy_tickers_json, proxy_weights_json, illiquidity_scalar, notes, is_active)
        VALUES (:id, :basket_key, :factor_key, :name, :asset_class, :sector, :region, :market_segment, :proxy_tickers_json, :proxy_weights_json, :illiquidity_scalar, :notes, :is_active)
        """
    )
    stress_insert = sa.text(
        """
        INSERT INTO stress_scenarios
        (id, scenario_key, name, description, severity, sort_order, shock_json, is_active)
        VALUES (:id, :scenario_key, :name, :description, :severity, :sort_order, :shock_json, :is_active)
        """
    )
    conn = op.get_bind()  # noqa: deprecated — using Alembic 1.x compat; upgrade to op.get_context().bind when Alembic ≥ 2.0 is pinned
    for index, basket in enumerate(PROXY_BASKETS, start=1):
        conn.execute(
            proxy_insert,
            {
                "id": f"overlay-proxy-{index:02d}",
                "basket_key": basket[0],
                "factor_key": basket[1],
                "name": basket[2],
                "asset_class": basket[3],
                "sector": basket[4],
                "region": basket[5],
                "market_segment": basket[6],
                "proxy_tickers_json": basket[7],
                "proxy_weights_json": basket[8],
                "illiquidity_scalar": basket[9],
                "notes": basket[10],
                "is_active": True,
            },
        )
    for index, scenario in enumerate(STRESS_SCENARIOS, start=1):
        conn.execute(
            stress_insert,
            {
                "id": f"overlay-stress-{index:02d}",
                "scenario_key": scenario[0],
                "name": scenario[1],
                "description": scenario[2],
                "severity": scenario[3],
                "sort_order": scenario[4],
                "shock_json": scenario[5],
                "is_active": True,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_risk_regimes_as_of_date", table_name="risk_regimes")
    op.drop_index("ix_risk_regimes_snapshot_id", table_name="risk_regimes")
    op.drop_index("ix_risk_regimes_workspace_id", table_name="risk_regimes")
    op.drop_table("risk_regimes")
    op.drop_table("stress_scenarios")
    op.drop_index("ix_proxy_baskets_factor_key", table_name="proxy_baskets")
    op.drop_table("proxy_baskets")
    op.drop_index("ix_asset_factor_exposures_as_of_date", table_name="asset_factor_exposures")
    op.drop_index("ix_asset_factor_exposures_factor_key", table_name="asset_factor_exposures")
    op.drop_index("ix_asset_factor_exposures_position_id", table_name="asset_factor_exposures")
    op.drop_index("ix_asset_factor_exposures_snapshot_id", table_name="asset_factor_exposures")
    op.drop_index("ix_asset_factor_exposures_workspace_id", table_name="asset_factor_exposures")
    op.drop_table("asset_factor_exposures")
    op.drop_index("ix_factor_scores_as_of_date", table_name="factor_scores")
    op.drop_index("ix_factor_scores_factor_key", table_name="factor_scores")
    op.drop_index("ix_factor_scores_workspace_id", table_name="factor_scores")
    op.drop_table("factor_scores")
    op.drop_column("positions", "factor_market_segment")
    op.drop_column("positions", "factor_region")
    op.drop_column("positions", "factor_subsector")
    op.drop_column("positions", "factor_sector")
    op.drop_column("positions", "factor_asset_class")
