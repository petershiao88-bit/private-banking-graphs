"""Render the exported RDF review graph as matching PNG and editable SVG.

Uses the existing system Python/Pillow, leaving project dependencies unchanged.
"""

import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "rdf-review-v0.6.0"
FH = "https://example.org/ontology/holding#"
BANK = "https://example.org/ontology/bank#"
W, H = 2600, 1810
FONT = "C:/Windows/Fonts/msjh.ttc"
BOLD = "C:/Windows/Fonts/msjhbd.ttc"
BG, INK, MUTED = "#ffffff", "#202b3a", "#536174"
BLUE, GRAY = "#275ba8", "#738295"
HOLD, BANK_FILL = "#eef4fc", "#fff3df"
image = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(image)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>客戶360 RDF v0.6.0 節點關係圖</title>',
       '<desc>17個類別、4條業務關係、12條繼承關係；8個資料屬性列在適用類別內。金控和銀行以區域與文字標示。</desc>',
       f'<rect width="{W}" height="{H}" fill="{BG}"/>']


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def rect(box, fill, outline=None, radius=18, width=2):
    x, y, w, h = box
    draw.rounded_rectangle((x, y, x+w, y+h), radius, fill, outline, width)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
               f'stroke="{outline or "none"}" stroke-width="{width}"/>')


def text(x, y, value, size=28, color=INK, bold=False, center=False):
    f = font(size, bold)
    if center:
        x -= draw.textlength(value, font=f)/2
    draw.text((x, y), value, font=f, fill=color, anchor="lt")
    svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" '
               f'font-family="Microsoft JhengHei,sans-serif" font-size="{size}" '
               f'font-weight="{700 if bold else 400}" fill="{color}">{html.escape(value)}</text>')


def path(points, color=GRAY, dashed=False, arrow=True, width=3):
    for a, b in zip(points, points[1:]):
        if dashed:
            length = math.dist(a, b)
            for distance in range(0, int(length), 18):
                start, end = distance/length, min(distance+10, length)/length
                p = tuple(a[i]+(b[i]-a[i])*start for i in range(2))
                q = tuple(a[i]+(b[i]-a[i])*end for i in range(2))
                draw.line((p, q), fill=color, width=width)
        else:
            draw.line((a, b), fill=color, width=width)
    coords = " ".join(f"{x},{y}" for x,y in points)
    dash = ' stroke-dasharray="10 8"' if dashed else ''
    svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>')
    if arrow:
        tip, prior = points[-1], points[-2]
        angle = math.atan2(tip[1]-prior[1], tip[0]-prior[0])
        back = (tip[0]-18*math.cos(angle), tip[1]-18*math.sin(angle))
        left = (back[0]+8*math.sin(angle), back[1]-8*math.cos(angle))
        right = (back[0]-8*math.sin(angle), back[1]+8*math.cos(angle))
        poly = [tip,left,right]
        draw.polygon(poly, fill=BG if dashed else color)
        draw.line(poly+[tip], fill=color, width=3)
        svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in poly)+f'" fill="{BG if dashed else color}" stroke="{color}" stroke-width="2"/>')


def edge_label(x, y, value, size=27, color=BLUE):
    width = draw.textlength(value, font=font(size)) + 20
    rect((x-width/2, y-5, width, size+15), BG, radius=6)
    text(x, y, value, size, color, center=True)


def main():
    data = json.loads((OUT / "rdf-graph.json").read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in data["nodes"]}
    positions = {
        FH+"Employee": (190,360,300,110), FH+"Customer": (710,360,320,110),
        FH+"ContactInformation": (1240,360,350,110), FH+"FinancialProduct": (2040,360,360,110),
        FH+"MobileContactInformation": (1070,660,380,170),
        FH+"AddressContactInformation": (590,610,420,300),
        FH+"Metric": (2040,720,360,110), FH+"FeeIncome": (1530,720,390,110),
        BANK+"BankEmployee": (190,1060,330,170), BANK+"BankFeeIncome": (760,1060,470,135),
    }
    products = ["DepositProduct","TWDFinancialProduct","ForeignCurrencyFinancialProduct",
                "StructuredFinancialProduct","StockProduct","BondProduct","OverseasFinancialProduct"]
    for i, key in enumerate(products):
        positions[BANK+key] = (90+i*350,1350,300,145)
    if set(positions) != set(nodes):
        raise ValueError("Layout must cover every current RDF class exactly once")
    text(70,55,"客戶360｜目前 RDF 結構",52,bold=True)
    text(72,135,f'v{data["version"]}　·　17 個類別　·　4 條業務關係　·　8 個資料屬性',28,MUTED)
    path([(80,220),(185,220)],BLUE,width=4)
    text(210,202,"業務關係（箭頭指向對象）",27)
    path([(720,220),(825,220)],GRAY,dashed=True)
    text(850,202,"繼承（子類別 → 父類別）",27)
    text(1420,202,"節點內列出資料屬性；所有欄位型別均為字串",27,MUTED)
    rect((50,270,2500,680),"#f7f9fd",radius=22)
    rect((50,1000,2500,550),"#fffaf1",radius=22)
    text(80,288,"金控｜共通語意",31,bold=True)
    text(80,1018,"銀行｜共通類別",31,bold=True)

    routes = {
        (FH+"Employee",FH+"Customer"): [(490,415),(710,415)],
        (FH+"Customer",FH+"ContactInformation"): [(1030,415),(1240,415)],
        (FH+"Customer",FH+"FinancialProduct"): [(870,360),(870,325),(2220,325),(2220,360)],
        (FH+"Metric",FH+"FinancialProduct"): [(2220,720),(2220,470)],
        (FH+"MobileContactInformation",FH+"ContactInformation"): [(1260,660),(1260,565),(1415,565),(1415,470)],
        (FH+"AddressContactInformation",FH+"ContactInformation"): [(800,610),(800,540),(1210,540),(1210,440),(1240,440)],
        (FH+"FeeIncome",FH+"Metric"): [(1920,775),(2040,775)],
        (BANK+"BankEmployee",FH+"Employee"): [(340,1060),(340,470)],
        (BANK+"BankFeeIncome",FH+"FeeIncome"): [(995,1060),(995,980),(1725,980),(1725,830)],
    }
    for i, key in enumerate(products):
        center = 240+i*350
        routes[(BANK+key,FH+"FinancialProduct")] = [(center,1350),(center,1280),(2510,1280),(2510,415),(2400,415)]
    actual = {(e["source"],e["target"]) for e in data["edges"]}
    if actual != set(routes):
        raise ValueError("Every explicit RDF relation must have a matching route")
    for edge in data["edges"]:
        if edge["source"] in {BANK+key for key in products}:
            branch = routes[(edge["source"],edge["target"])][:2]
            path(branch,GRAY,dashed=True,arrow=False)
            continue
        path(routes[(edge["source"],edge["target"])],BLUE if edge["kind"] == "relationship" else GRAY,
             dashed=edge["kind"] == "subclass",width=4 if edge["kind"] == "relationship" else 3)
    # Draw the shared inheritance bus once so overlaid dash patterns do not fill gaps.
    path([(240,1280),(2510,1280),(2510,415),(2400,415)],GRAY,dashed=True)

    labels = [(600,374,"服務客戶"),(1135,374,"具有通聯資訊"),(1750,291,"持有金融商品"),
              (2370,575,"衡量金融商品")]
    for x,y,value in labels:
        edge_label(x,y,value)
    for x,y in ((1050,505),(1360,580),(1980,738),(385,960),(1600,946)):
        edge_label(x,y,"繼承",25,GRAY)
    text(1370,1070,"商品種類／幣別／結構／投資範圍",28,MUTED)
    text(1370,1120,"下方七個類別皆直接繼承「金融商品」",28,MUTED)
    text(1370,1170,"分類可重疊；目前未宣告互斥",26,MUTED)

    for uri, box in positions.items():
        node = nodes[uri]
        x,y,w,h = box
        fill = HOLD if node["owner"] == "holding" else BANK_FILL
        rect(box,fill,"#b9c5d4",radius=18)
        label = node["label"]
        if draw.textlength(label,font=font(33,True)) > w-28:
            raise ValueError(f"Node label exceeds its card: {label}")
        text(x+w/2,y+25,label,33,bold=True,center=True)
        if node["properties"]:
            draw.line((x+18,y+75,x+w-18,y+75),fill="#b9c5d4",width=1)
            svg.append(f'<line x1="{x+18}" y1="{y+75}" x2="{x+w-18}" y2="{y+75}" stroke="#b9c5d4"/>')
            order = {key:i for i,key in enumerate(("mobileNumber","countryCode","city","district","addressLine","postalCode","fullAddress","employeeId"))}
            props = sorted(node["properties"],key=lambda p:order[p["id"].split("#")[-1]])
            for i, prop in enumerate(props):
                text(x+25,y+94+i*31,prop["label"]+"：字串",25)
        else:
            text(x+w/2,y+76,"類別",23,MUTED,center=True)

    rect((50,1590,2500,170),"#f7f8fa",radius=18)
    text(80,1610,"模型註記："+"、".join(a["label"] for a in data["annotations"]),27)
    text(80,1660,"此圖為 RDF 結構投影；業務箭頭依 domain／range 繪製，並非真實人員或客戶資料。",27,MUTED)
    text(80,1710,"本圖尚未合併部門 PG：理專、商品手收與底表映射。",27,MUTED)
    svg.append('</svg>')
    image.save(OUT/"rdf-graph.png",optimize=True)
    (OUT/"rdf-graph.svg").write_text("\n".join(svg),encoding="utf-8")
    print("Rendered RDF graph PNG and SVG:",OUT)


if __name__ == "__main__":
    main()
