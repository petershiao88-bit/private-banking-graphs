"""Render the validated AUM/Income shared-product concept graph only."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "Shared_product_layout_data.json").read_text(encoding="utf-8"))
FONT = FontProperties(fname=r"C:\Windows\Fonts\msjh.ttc")

COLORS = {
    "aum": ("#E2F0FF", "#2269B3"),
    "product": ("#E8F5E9", "#40824B"),
    "income": ("#FFE9DE", "#D15B22"),
    "pending": ("#FFF4DA", "#B98522"),
}

metric_positions = {
    "aum:metric:aum_total_month_end": (1.0, 8.0),
    "aum:metric:aum_investment_month_end": (3.5, 8.0),
    "aum:metric:aum_bank_investment_month_end": (5.9, 9.5),
    "aum:metric:aum_securities_month_end": (6.1, 2.5),
    "aum:metric:aum_insurance_month_end": (6.1, 14.0),
    "aum:metric:aum_deposit_month_end": (6.1, 15.0),
    "income:metric:income_total_customer_month": (18.5, 8.0),
    "income:metric:fee_income": (16.0, 8.0),
    "income:metric:interest_income": (16.0, 14.0),
    "income:metric:bank_fee_income": (13.6, 9.5),
    "income:metric:securities_fee_income": (13.4, 2.5),
    "income:metric:deposit_interest_income": (13.4, 15.0),
}

nodes = {node["key"]: node for node in DATA["nodes"]}
products = sorted(
    (node for node in DATA["nodes"] if node["side"] == "pb_shared"),
    key=lambda node: node["displayOrder"],
)
positions = dict(metric_positions)
positions.update({node["key"]: (9.75, 15.0 - index) for index, node in enumerate(products)})

fig, ax = plt.subplots(figsize=(20.5, 16), dpi=165)
fig.patch.set_facecolor("#FBFCFE")
ax.set_facecolor("#FBFCFE")
ax.set_xlim(-0.3, 19.8)
ax.set_ylim(-1.0, 17.5)
ax.axis("off")


def label(key: str) -> str:
    return nodes[key]["name"]


def box(key: str, x: float, y: float) -> None:
    node = nodes[key]
    if node["side"] == "pb_shared":
        fill, border = COLORS["pending"] if node["code"] == "bank_collective_account" else COLORS["product"]
        width, height = 2.8, 0.62
    else:
        fill, border = COLORS[node["side"]]
        width, height = 2.0, 0.68
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        linewidth=1.45, edgecolor=border, facecolor=fill, zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x, y, label(key), ha="center", va="center", fontsize=11.3,
            color="#263238", fontproperties=FONT, zorder=4)


def edge(source: str, target: str, relation: str) -> None:
    sx, sy = positions[source]
    tx, ty = positions[target]
    sign = 1 if tx > sx else -1
    sw = 2.8 if nodes[source]["side"] == "pb_shared" else 2.0
    tw = 2.8 if nodes[target]["side"] == "pb_shared" else 2.0
    start = (sx + sign * sw / 2, sy)
    end = (tx - sign * tw / 2, ty)
    pending = relation == "INCOME_DEFINITION_PENDING"
    hierarchy = relation.endswith("ROLLS_UP_TO")
    family = "aum" if relation.startswith("AUM_") or relation == "MEASURED_BY_AUM" else "income"
    color = COLORS[family][1]
    patch = FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=9.5,
        linewidth=1.65 if hierarchy or pending else 1.15,
        linestyle="--" if pending else "-",
        color=color, alpha=0.78 if hierarchy or pending else 0.36,
        connectionstyle="arc3,rad=0.0", zorder=1,
    )
    ax.add_patch(patch)


for item in DATA["edges"]:
    edge(item["source"], item["target"], item["type"])
for key, (x, y) in positions.items():
    box(key, x, y)

ax.text(9.75, 17.0, "AUM × Income 共用概念圖", ha="center", fontsize=22,
        weight="bold", color="#243447", fontproperties=FONT)
ax.text(9.75, 16.48, "15 個共用產品概念  •  兩側獨立指標體系  •  箭頭表示產品對應指標及逐層彙總",
        ha="center", fontsize=10.8, color="#526171", fontproperties=FONT)
ax.text(3.5, 15.8, "AUM｜資產管理規模", ha="center", fontsize=13,
        color=COLORS["aum"][1], weight="bold", fontproperties=FONT)
ax.text(9.75, 15.8, "共用產品概念", ha="center", fontsize=13,
        color="#40824B", weight="bold", fontproperties=FONT)
ax.text(16.5, 15.8, "Income｜收入", ha="center", fontsize=13,
        color=COLORS["income"][1], weight="bold", fontproperties=FONT)
ax.text(9.75, -0.15, "藍色：AUM｜橘色：Income｜虛線：集合管理帳戶的 Income 定義待確認。概念連線不表示兩者可相加或使用相同公式。",
        ha="center", fontsize=10, color="#677482", fontproperties=FONT)

for suffix in ("png", "svg"):
    fig.savefig(HERE / f"AUM_Income_shared_concept_graph.{suffix}",
                bbox_inches="tight", pad_inches=0.25, facecolor=fig.get_facecolor())
plt.close(fig)
