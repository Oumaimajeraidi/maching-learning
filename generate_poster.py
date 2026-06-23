# -*- coding: utf-8 -*-
"""
Poster scientifique A0 — TOX21 Multi-Label Machine Learning
Style inspire du poster OpportMatch (FSBM / Hassan II)
"""

from reportlab.pdfgen import canvas as CV
from reportlab.lib.pagesizes import A0
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.utils import simpleSplit
import os

# ── Page A0 Portrait ─────────────────────────────────────────
PW, PH = A0  # 2383.94 × 3370.39 pt

# ── Palette couleurs ─────────────────────────────────────────
NAVY    = HexColor('#0f1e35')
NAVY2   = HexColor('#061220')
BLUE    = HexColor('#1a56db')
BLUE_D  = HexColor('#1e40af')
BLUE_L  = HexColor('#dbeafe')
BLUE_M  = HexColor('#60a5fa')
TEAL    = HexColor('#0d9488')
TEAL_L  = HexColor('#ccfbf1')
GREEN   = HexColor('#15803d')
GREEN_L = HexColor('#dcfce7')
RED     = HexColor('#b91c1c')
RED_L   = HexColor('#fee2e2')
AMBER   = HexColor('#92400e')
AMBER_L = HexColor('#fef3c7')
GRAY_D  = HexColor('#1e293b')
GRAY_M  = HexColor('#475569')
GRAY_L  = HexColor('#e2e8f0')
GRAY_LL = HexColor('#f8fafc')
W       = white

# ── Fonts (built-in Helvetica) ────────────────────────────────
FN = 'Helvetica'
FB = 'Helvetica-Bold'
FI = 'Helvetica-Oblique'

# ── Layout ────────────────────────────────────────────────────
MG  = 60.0
GAP = 68.0
CW  = (PW - 2*MG - GAP) / 2   # ~1097 pt each column
LX  = MG
RX  = MG + CW + GAP


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def fr(c, x, y, w, h, color, radius=0):
    """Filled rectangle."""
    c.setFillColor(color)
    if radius > 0:
        c.roundRect(x, y, w, h, radius, stroke=0, fill=1)
    else:
        c.rect(x, y, w, h, stroke=0, fill=1)


def br(c, x, y, w, h, stroke_color, lw=2, radius=0):
    """Border-only rectangle."""
    c.setStrokeColor(stroke_color)
    c.setLineWidth(lw)
    c.setFillColor(GRAY_LL)  # transparent workaround
    if radius > 0:
        c.roundRect(x, y, w, h, radius, stroke=1, fill=0)
    else:
        c.rect(x, y, w, h, stroke=1, fill=0)


def fbr(c, x, y, w, h, fill, stroke, lw=2, radius=0):
    """Filled + bordered rectangle."""
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    if radius > 0:
        c.roundRect(x, y, w, h, radius, stroke=1, fill=1)
    else:
        c.rect(x, y, w, h, stroke=1, fill=1)


def pt(c, x, y, txt, font=FN, size=24, color=GRAY_D, align='l'):
    """Place text."""
    c.setFont(font, size)
    c.setFillColor(color)
    if align == 'c':
        c.drawCentredString(x, y, txt)
    elif align == 'r':
        c.drawRightString(x, y, txt)
    else:
        c.drawString(x, y, txt)


def wt(c, x, y_top, w, txt, font=FN, size=24, color=GRAY_D, lhf=1.35):
    """Wrapped text block. y_top = top baseline anchor. Returns bottom y."""
    lh    = size * lhf
    lines = simpleSplit(txt, font, size, w)
    c.setFont(font, size)
    c.setFillColor(color)
    y = y_top
    for ln in lines:
        c.drawString(x, y, ln)
        y -= lh
    return y + lh   # bottom of last line


def hline(c, x, y, w, color=GRAY_L, lw=2):
    c.setStrokeColor(color)
    c.setLineWidth(lw)
    c.line(x, y, x + w, y)


def section(c, x, y_top, w, h, title, icon_txt, hdr_color=BLUE):
    """
    Draw a section box.
    Returns (content_y_top, content_x, content_w)
    """
    HDR = 72
    # White body
    fbr(c, x, y_top - h, w, h, W, GRAY_L, lw=2, radius=18)
    # Header (filled rounded for top, square for overlap at bottom)
    fr(c, x, y_top - HDR, w, HDR - 18, hdr_color)
    c.setFillColor(hdr_color)
    c.roundRect(x, y_top - HDR, w, HDR, 18, stroke=0, fill=1)
    # Mask bottom corners of header to look flat at bottom
    fr(c, x, y_top - HDR, w, 18, hdr_color)
    # Title text
    pt(c, x + 28, y_top - HDR + 22, f'{icon_txt}  {title}', FB, 34, W)
    return y_top - HDR - 30, x + 28, w - 56


def metric_cell(c, x, y, w, h, value, label, v_color=BLUE):
    """Small metric box."""
    fbr(c, x, y, w, h, W, GRAY_L, lw=1.5, radius=12)
    pt(c, x + w/2, y + h*0.55, value, FB, 38, v_color, 'c')
    pt(c, x + w/2, y + h*0.22, label, FN, 20, GRAY_M, 'c')


def bullet_item(c, x, y, w, txt, dot_color=BLUE, size=23):
    """Bullet point."""
    fr(c, x + 2, y + size*0.3, 12, 12, dot_color, radius=3)
    wt(c, x + 22, y + size*0.9, w - 22, txt, FN, size, GRAY_D)


def step_box(c, x, y, w, h, num, title, desc, color=BLUE):
    """Flowchart step box."""
    fr(c, x, y, w, h, color, radius=14)
    pt(c, x + w/2, y + h - 26, num, FB, 28, W, 'c')
    hline(c, x + 15, y + h - 34, w - 30, BLUE_M, 1)
    pt(c, x + w/2, y + h*0.55, title, FB, 24, W, 'c')
    wt(c, x + 12, y + h*0.38, w - 24, desc, FN, 19, BLUE_L, 1.3)


def data_row(c, x, y, cols_data, col_ws, row_h, is_header=False):
    """Draw a table row."""
    bg = NAVY if is_header else (W if (y % (row_h * 2) > row_h * 0.5) else GRAY_LL)
    fr(c, x, y, sum(col_ws), row_h, bg)
    cx = x + 8
    for i, (txt, w_) in enumerate(zip(cols_data, col_ws)):
        font = FB if is_header else FN
        color = W if is_header else GRAY_D
        pt(c, cx, y + row_h * 0.28, txt, font, 20 if is_header else 19, color)
        cx += w_


# ══════════════════════════════════════════════════════════════
# DRAW POSTER
# ══════════════════════════════════════════════════════════════

def draw_poster(output_path):
    c = CV.Canvas(output_path, pagesize=(PW, PH))

    # ── BACKGROUND ───────────────────────────────────────────
    fr(c, 0, 0, PW, PH, GRAY_LL)

    # ══════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════
    HDR_H = 430
    fr(c, 0, PH - HDR_H, PW, HDR_H, NAVY)
    fr(c, 0, PH - HDR_H, PW, 10, BLUE)

    # -- Left: University info
    pt(c, MG, PH - 75, "FACULTE DES SCIENCES BEN M'SICK", FB, 30, BLUE_M)
    pt(c, MG, PH - 115, "UNIVERSITE HASSAN II DE CASABLANCA", FN, 25, GRAY_L)
    hline(c, MG, PH - 130, 480, BLUE, 2.5)
    pt(c, MG, PH - 165, "Master Data Science & Big Data", FI, 23, GRAY_M)

    # Logo circle (FSBM)
    c.setFillColor(BLUE_D)
    c.circle(MG + 80, PH - 330, 80, stroke=0, fill=1)
    c.setFillColor(BLUE_M)
    c.circle(MG + 80, PH - 330, 80, stroke=1, fill=0)
    c.setLineWidth(3)
    pt(c, MG + 80, PH - 315, "FS", FB, 36, W, 'c')
    pt(c, MG + 80, PH - 358, "BM", FB, 36, W, 'c')

    # -- Center: Title
    CX = PW / 2
    pt(c, CX, PH - 80, "TOX21 : Prediction de Toxicite Moleculaire", FB, 60, W, 'c')
    pt(c, CX, PH - 150, "par Machine Learning Multi-Label", FB, 50, BLUE_M, 'c')
    pt(c, CX, PH - 208,
       "Classification simultanee de 12 cibles biologiques via Random Forest et SHAP Explainability",
       FI, 28, GRAY_L, 'c')
    hline(c, 350, PH - 228, PW - 700, BLUE, 2)
    pt(c, CX, PH - 270, "[Prenom NOM]", FB, 32, W, 'c')
    pt(c, CX, PH - 310, "Encadre par le Prof. [Superviseur]", FI, 27, BLUE_M, 'c')
    pt(c, CX, PH - 350,
       "Master Data Science & Big Data  -  Faculte des Sciences Ben M'Sick  -  2025/2026",
       FN, 24, GRAY_L, 'c')

    # -- Right: Badge Data Science
    bx2 = PW - MG - 200
    fbr(c, bx2, PH - 420, 200, 200, BLUE_D, BLUE_M, lw=3, radius=15)
    pt(c, bx2 + 100, PH - 268, "Data", FB, 26, W, 'c')
    pt(c, bx2 + 100, PH - 298, "Science", FB, 26, W, 'c')
    pt(c, bx2 + 100, PH - 330, "& Big Data", FB, 22, W, 'c')
    hline(c, bx2 + 20, PH - 346, 160, BLUE_M, 1.5)
    pt(c, bx2 + 100, PH - 368, "Master S2", FN, 20, BLUE_M, 'c')

    # ── STATS BAR ─────────────────────────────────────────────
    STATS_H = 90
    STATS_Y = PH - HDR_H - STATS_H
    fr(c, 0, STATS_Y, PW, STATS_H, NAVY2)
    stats = [
        ("12",    "Cibles biologiques"),
        ("8 014", "Molecules"),
        ("2 063", "Features"),
        ("0.783", "AUC-ROC macro"),
        ("0.031", "Hamming Loss"),
        ("200",   "Arbres RF"),
        ("15",    "Descripteurs"),
        ("2 048", "Bits Morgan"),
    ]
    sw = PW / len(stats)
    for i, (val, lbl) in enumerate(stats):
        sx = i * sw + sw / 2
        pt(c, sx, STATS_Y + 55, val, FB, 30, BLUE_M, 'c')
        pt(c, sx, STATS_Y + 22, lbl, FN, 18, GRAY_M, 'c')
        if i > 0:
            hline(c, i * sw, STATS_Y + 15, 0, GRAY_D, 1)
            c.setStrokeColor(GRAY_D)
            c.setLineWidth(1)
            c.line(i * sw, STATS_Y + 10, i * sw, STATS_Y + 80)

    # ══════════════════════════════════════════════════════════
    # BODY
    # ══════════════════════════════════════════════════════════
    BODY_TOP = STATS_Y - 35   # ~2815
    FOOT_Y   = 215

    # ══ LEFT COLUMN ══════════════════════════════════════════

    # ---- INTRODUCTION (left) --------------------------------
    INTRO_H = 750
    iy = BODY_TOP
    cy, cx, cw = section(c, LX, iy, CW, INTRO_H, "INTRODUCTION", "[I]")

    wt(c, cx, cy, cw,
       "Le programme TOX21 (National Institutes of Health / EPA / FDA) "
       "vise a tester la toxicite de milliers de substances chimiques via des tests "
       "biologiques automatises (High-Throughput Screening). "
       "Les methodes experimentales traditionnelles sont lentes (semaines/molecule), "
       "couteuses et soumises a des contraintes ethiques liees a l'experimentation animale.",
       FN, 23, GRAY_D, 1.38)

    cy2 = cy - 185
    hline(c, cx, cy2 + 10, cw, GRAY_L, 1.5)
    cy2 -= 25
    pt(c, cx, cy2, "Objectif du projet :", FB, 25, BLUE_D)
    cy2 -= 38
    wt(c, cx, cy2, cw,
       "Construire un systeme de prediction automatique qui, a partir "
       "de la simple notation SMILES d'une molecule, predit simultanement "
       "son potentiel toxique sur 12 cibles biologiques differentes - "
       "sans aucun test experimentale.",
       FN, 23, GRAY_D, 1.38)

    # Diagram SMILES → Model → 12 outputs
    diag_y = iy - INTRO_H + 230
    # SMILES box
    fbr(c, cx, diag_y, 290, 75, NAVY, BLUE, lw=2, radius=10)
    pt(c, cx + 145, diag_y + 50, "SMILES", FB, 25, W, 'c')
    pt(c, cx + 145, diag_y + 22, "CC(=O)Oc1ccccc1...", FI, 18, BLUE_M, 'c')
    # Arrow
    pt(c, cx + 310, diag_y + 35, "-->", FB, 28, BLUE)
    # Model box
    fbr(c, cx + 345, diag_y, 260, 75, BLUE, BLUE_D, lw=2, radius=10)
    pt(c, cx + 475, diag_y + 50, "Random Forest", FB, 23, W, 'c')
    pt(c, cx + 475, diag_y + 22, "MultiOutput x12", FN, 19, BLUE_L, 'c')
    # Arrow
    pt(c, cx + 625, diag_y + 35, "-->", FB, 28, BLUE)
    # Output box
    fbr(c, cx + 665, diag_y, 310, 75, TEAL, TEAL, lw=2, radius=10)
    pt(c, cx + 820, diag_y + 50, "12 scores", FB, 23, W, 'c')
    pt(c, cx + 820, diag_y + 22, "P(toxique) par cible", FN, 18, TEAL_L, 'c')

    # ---- PROBLEMATIQUE (left) --------------------------------
    PROB_H = 600
    py = iy - INTRO_H - 38
    cy, cx, cw = section(c, LX, py, CW, PROB_H, "PROBLEMATIQUE", "[P]")

    wt(c, cx, cy, cw,
       "Le principal defi ne reside pas seulement dans la prediction mais dans la complexite "
       "du probleme : chaque molecule doit etre evaluee sur 12 cibles simultanement, "
       "avec des classes fortement desequilibrees (3 a 15 % de positifs) et "
       "jusqu'a 40 % de valeurs manquantes selon la cible.",
       FN, 23, GRAY_D, 1.38)

    # 3 challenge cards
    cards = [
        ("Desequilibre", "3-15 % positifs\npar cible", RED_L, RED),
        ("Val. manquantes", "15-40 % NaN\nselon la cible", AMBER_L, AMBER),
        ("Multi-Label", "12 outputs\nsimultanes", BLUE_L, BLUE_D),
    ]
    cy3 = cy - 200
    cw3 = (cw - 40) / 3
    for i, (title, desc, bg, clr) in enumerate(cards):
        bx3 = cx + i * (cw3 + 20)
        fbr(c, bx3, cy3 - 140, cw3, 140, bg, clr, lw=2, radius=12)
        fr(c, bx3, cy3 - 38, cw3, 38, clr, radius=12)
        fr(c, bx3, cy3 - 38, cw3, 19, clr)  # flat bottom of top bar
        pt(c, bx3 + cw3/2, cy3 - 20, title, FB, 23, W, 'c')
        for j, d in enumerate(desc.split('\n')):
            pt(c, bx3 + cw3/2, cy3 - 80 - j*32, d, FB, 24, clr, 'c')

    cy4 = cy3 - 165
    pt(c, cx, cy4, "Notre approche — Binary Relevance :", FB, 25, NAVY)
    cy4 -= 40
    for b_txt in [
        "1 classifieur Random Forest independant par cible biologique (12 au total)",
        "class_weight='balanced' pour compenser le desequilibre des classes",
        "Suppression des NaN par cible (dropna individuel) avant entrainement",
    ]:
        bullet_item(c, cx, cy4, cw, b_txt, BLUE, 23)
        cy4 -= 60

    # ---- PIPELINE METHODOLOGIQUE (left) ----------------------
    PIPE_H = 780
    ppy = py - PROB_H - 38
    cy, cx, cw = section(c, LX, ppy, CW, PIPE_H, "PIPELINE METHODOLOGIQUE", "[M]")

    steps = [
        ("01", "Donnees", "tox21.csv\n8 014 SMILES"),
        ("02", "Features", "RDKit\n2 063 dims"),
        ("03", "Split", "80/20\nfixe"),
        ("04", "Train", "12 RF\nparallele"),
        ("05", "Eval.", "AUC ROC\nHamming"),
        ("06", "Deploy", "Streamlit\n+ SHAP"),
    ]
    sw2  = (cw - 10) / 6
    sy   = cy - 20
    sh   = 165
    for i, (num, ttl, dsc) in enumerate(steps):
        sx2 = cx + i * sw2
        clr_s = NAVY if i in (0, 5) else (TEAL if i == 4 else BLUE)
        step_box(c, sx2, sy - sh, sw2 - 8, sh, num, ttl, dsc, clr_s)
        if i < 5:
            # arrow between boxes
            pt(c, sx2 + sw2 - 12, sy - sh/2 - 6, ">", FB, 22, BLUE_M)

    cy5 = sy - sh - 40
    pt(c, cx, cy5, "Detail des etapes :", FB, 25, NAVY)
    cy5 -= 38

    pipe_details = [
        ("Chargement", "Lecture tox21.csv, parsage SMILES via RDKit, creation du dataframe multi-label"),
        ("Feature Eng.", "15 descripteurs physico + Morgan ECFP4 (r=2, 2048 bits) -> vecteur de 2063"),
        ("Split 80/20",  "random_state=42 -> 6 411 mol. train / 1 603 mol. validation / 2 459 test"),
        ("Entrainement", "MultiOutputClassifier(RandomForest, n_jobs=-1) -> 12 RF en parallele"),
        ("Evaluation",   "AUC-ROC macro, Hamming Loss, F1 micro/macro, Jaccard score par cible"),
        ("Deploiement",  "app.py Streamlit -> prediction + SHAP + viewer 3D moleculaire py3Dmol"),
    ]
    for step_lbl, step_desc in pipe_details:
        pt(c, cx, cy5, f"  {step_lbl} :", FB, 22, BLUE_D)
        cy5 -= 32
        wt(c, cx + 20, cy5, cw - 20, step_desc, FN, 21, GRAY_D, 1.3)
        cy5 -= 72

    # ══ RIGHT COLUMN ═════════════════════════════════════════

    # ---- FEATURE ENGINEERING (right) ------------------------
    FEAT_H = 690
    fy = BODY_TOP
    cy, cx, cw = section(c, RX, fy, CW, FEAT_H, "FEATURE ENGINEERING", "[F]")

    # 3 cards: 15 + 2048 = 2063
    for i, (val, lbl, sub, clr, bg) in enumerate([
        ("15",    "Descripteurs",     "Proprietes physicochimiques\ncalculees par RDKit", BLUE,  BLUE_L),
        ("+",     "",                 "",                                                  GRAY_M, GRAY_LL),
        ("2 048", "Bits Morgan",      "Empreintes ECFP4\nr=2 voisinage circulaire",       TEAL,  TEAL_L),
    ]):
        if val == "+":
            pt(c, cx + cw*0.45, cy - 80, "+", FB, 52, GRAY_M, 'c')
            continue
        bx_i = cx + (0 if i == 0 else cw*0.5 + 20)
        bw_i = cw * 0.48
        fbr(c, bx_i, cy - 185, bw_i, 185, bg, clr, lw=2, radius=14)
        fr(c, bx_i, cy - 50, bw_i, 50, clr, radius=14)
        fr(c, bx_i, cy - 50, bw_i, 25, clr)
        pt(c, bx_i + bw_i/2, cy - 30, val, FB, 40, W, 'c')
        pt(c, bx_i + bw_i/2, cy - 80, lbl, FB, 26, clr, 'c')
        for j, s in enumerate(sub.split('\n')):
            pt(c, bx_i + bw_i/2, cy - 120 - j*32, s, FN, 21, GRAY_D, 'c')

    cy6  = cy - 210
    pt(c, cx, cy6, "= 2 063 features totales par molecule", FB, 27, NAVY)
    cy6 -= 40
    hline(c, cx, cy6 + 5, cw, GRAY_L, 1.5)
    cy6 -= 28

    # Table descripteurs
    desc_table = [
        ["Descripteur",   "Description",               "Role toxicologique"],
        ["MolWt",         "Poids moleculaire (g/mol)", "Accumulation >450 g/mol"],
        ["LogP",          "Lipophilicite",             "Passage membranes"],
        ["TPSA",          "Surface polaire (A2)",      "Absorption - BBB"],
        ["HBondDonors",   "Donneurs liaisons H",       "Affinite recepteurs"],
        ["AromaticRings", "Cycles aromatiques",        "Intercalation ADN"],
        ["FractionCSP3",  "Carbones sp3",              "Planarité molecule"],
        ["NumHeteroatoms","Heteroatomes N/O/S",        "Reactivite chimique"],
        ["MolMR",         "Refractivite molaire",      "Polarisabilite"],
    ]
    col_ws3 = [290, 330, 340]
    row_h3  = 44
    ty      = cy6
    for ri, row in enumerate(desc_table):
        is_hdr = ri == 0
        bg_row = NAVY if is_hdr else (GRAY_LL if ri % 2 == 0 else W)
        fr(c, cx, ty - row_h3, sum(col_ws3), row_h3, bg_row)
        rx2 = cx
        for ci2, (cell, cw2) in enumerate(zip(row, col_ws3)):
            fnt2 = FB if is_hdr else FN
            clr2 = W if is_hdr else GRAY_D
            pt(c, rx2 + 8, ty - row_h3 + 13, cell, fnt2, 20, clr2)
            rx2 += cw2
        # row border
        hline(c, cx, ty - row_h3, sum(col_ws3), GRAY_L, 1)
        ty -= row_h3

    # ---- RESULTATS (right) ----------------------------------
    RES_H = 960
    ry = fy - FEAT_H - 38
    cy, cx, cw = section(c, RX, ry, CW, RES_H, "RESULTATS", "[R]")

    # 3 metric cards
    mets = [
        ("0.783", "AUC-ROC Macro", BLUE),
        ("0.031", "Hamming Loss",  GREEN),
        ("0.237", "F1-Score Macro",GRAY_M),
    ]
    mw = (cw - 40) / 3
    for i, (val, lbl, clr) in enumerate(mets):
        mx2 = cx + i * (mw + 20)
        fbr(c, mx2, cy - 130, mw, 130, W, clr, lw=2, radius=12)
        fr(c, mx2, cy - 10, mw, 10, clr, radius=12)
        fr(c, mx2, cy - 10, mw, 6, clr)
        pt(c, mx2 + mw/2, cy - 68, val, FB, 46, clr, 'c')
        pt(c, mx2 + mw/2, cy - 112, lbl, FN, 21, GRAY_M, 'c')

    cy7 = cy - 150
    hline(c, cx, cy7 + 8, cw, GRAY_L, 1.5)
    cy7 -= 28
    pt(c, cx, cy7, "Performance AUC-ROC par cible biologique :", FB, 25, NAVY)
    cy7 -= 40

    # Table per-target AUC
    tgt_rows = [
        ["Cible",         "AUC-ROC", "Niveau",    "Cible",          "AUC-ROC", "Niveau"],
        ["NR-AhR",        "0.861",   "Excellent", "SR-ARE",         "0.826",   "Bon"],
        ["SR-MMP",        "0.847",   "Excellent", "SR-ATAD5",       "0.811",   "Bon"],
        ["NR-ER",         "0.793",   "Bon",       "SR-p53",         "0.781",   "Bon"],
        ["SR-HSE",        "0.769",   "Modere",    "NR-AR",          "0.752",   "Modere"],
        ["NR-ER-LBD",     "0.741",   "Modere",    "NR-AR-LBD",      "0.718",   "Modere"],
        ["NR-Aromatase",  "0.704",   "Modere",    "NR-PPAR-gamma",  "0.703",   "Modere"],
    ]
    col_ws4 = [260, 120, 130, 260, 120, 130]
    row_h4  = 46
    for ri, row in enumerate(tgt_rows):
        is_hdr = ri == 0
        bg_row = NAVY if is_hdr else (GRAY_LL if ri % 2 == 0 else W)
        fr(c, cx, cy7 - row_h4, sum(col_ws4), row_h4, bg_row)
        rx3 = cx
        for ci3, (cell, cw3) in enumerate(zip(row, col_ws4)):
            if not is_hdr and ci3 in (2, 5):
                # Color for level
                cell_clr = GREEN if cell == "Bon" else (BLUE if cell == "Excellent" else AMBER)
            else:
                cell_clr = W if is_hdr else GRAY_D
            fnt3 = FB if (is_hdr or ci3 in (2, 5)) else FN
            pt(c, rx3 + 8, cy7 - row_h4 + 14, cell, fnt3, 21, cell_clr if is_hdr else (cell_clr if ci3 in (2,5) else GRAY_D))
            rx3 += cw3
        hline(c, cx, cy7 - row_h4, sum(col_ws4), GRAY_L, 1)
        cy7 -= row_h4

    cy7 -= 20
    # Histogram visual (AUC bars)
    pt(c, cx, cy7, "Visualisation AUC-ROC par cible :", FB, 23, NAVY)
    cy7 -= 35
    aucs = [0.861, 0.847, 0.826, 0.811, 0.793, 0.781,
            0.769, 0.752, 0.741, 0.718, 0.704, 0.703]
    names = ["NR-AhR","SR-MMP","SR-ARE","SR-ATAD5","NR-ER","SR-p53",
             "SR-HSE","NR-AR","NR-ER-LBD","NR-AR-LBD","NR-Aro.","NR-PPAR"]
    bar_w = cw / 12 - 4
    bar_max = 130
    for i, (auc_val, name) in enumerate(zip(aucs, names)):
        bx4 = cx + i * (bar_w + 4)
        bar_h = int((auc_val - 0.65) / 0.25 * bar_max)
        clr4 = GREEN if auc_val >= 0.82 else (BLUE if auc_val >= 0.78 else AMBER)
        fr(c, bx4, cy7 - bar_max, bar_w, bar_h, clr4, radius=4)
        # value
        pt(c, bx4 + bar_w/2, cy7 - bar_max + bar_h + 5, f"{auc_val:.2f}", FN, 16, GRAY_D, 'c')
        # label
        c.setFont(FN, 14)
        c.setFillColor(GRAY_M)
        c.saveState()
        c.translate(bx4 + bar_w/2, cy7 - bar_max - 10)
        c.rotate(45)
        c.drawString(0, 0, name)
        c.restoreState()
    # Threshold line 0.8
    th_y = cy7 - bar_max + int((0.8 - 0.65) / 0.25 * bar_max)
    c.setStrokeColor(RED)
    c.setLineWidth(2)
    c.setDash(8, 4)
    c.line(cx, th_y, cx + cw, th_y)
    c.setDash()
    pt(c, cx + cw - 90, th_y + 6, "seuil 0.8", FI, 18, RED)

    # ---- CONCLUSION & PERSPECTIVES (right) ------------------
    CON_H = 510
    cony = ry - RES_H - 38
    cy, cx, cw = section(c, RX, cony, CW, CON_H,
                          "CONCLUSION & PERSPECTIVES", "[C]")

    # 2 columns inside
    hw = (cw - 30) / 2
    # Left: bilan
    fbr(c, cx, cy - 390, hw, 390, GRAY_LL, GRAY_L, lw=1.5, radius=10)
    fr(c, cx, cy - 38, hw, 38, GREEN, radius=10)
    fr(c, cx, cy - 38, hw, 19, GREEN)
    pt(c, cx + hw/2, cy - 22, "Bilan du Projet", FB, 24, W, 'c')
    bilan = [
        "Pipeline ML complet bout-en-bout",
        "AUC-ROC 0.783 - competitif en litterature",
        "Feature engineering chimique 2 063 dims",
        "Explainabilite SHAP par cible bio",
        "Interface Streamlit + viewer 3D",
        "Dark Mode + Historique analyses",
    ]
    by2 = cy - 75
    for b in bilan:
        bullet_item(c, cx + 12, by2, hw - 24, b, GREEN, 21)
        by2 -= 55

    # Right: perspectives
    px2 = cx + hw + 30
    fbr(c, px2, cy - 390, hw, 390, GRAY_LL, GRAY_L, lw=1.5, radius=10)
    fr(c, px2, cy - 38, hw, 38, BLUE, radius=10)
    fr(c, px2, cy - 38, hw, 19, BLUE)
    pt(c, px2 + hw/2, cy - 22, "Perspectives", FB, 24, W, 'c')
    persp = [
        "GNN - Graph Neural Networks",
        "XGBoost sur cibles difficiles",
        "Authentification Google OAuth",
        "Deploiement Streamlit Cloud",
        "SMOTE - ameliorer le F1",
        "Validation sur datasets externes",
    ]
    py3 = cy - 75
    for p in persp:
        bullet_item(c, px2 + 12, py3, hw - 24, p, BLUE, 21)
        py3 -= 55

    # ══════════════════════════════════════════════════════════
    # FULL-WIDTH BOTTOM : REFERENCES + CONTACT
    # ══════════════════════════════════════════════════════════
    REF_Y = FOOT_Y + 10
    REF_H = cony - CON_H - 28 - REF_Y

    fbr(c, MG, REF_Y, PW - 2*MG, REF_H, W, GRAY_L, lw=2, radius=18)
    fr(c, MG, REF_Y + REF_H - 60, PW - 2*MG, 60, NAVY, radius=18)
    fr(c, MG, REF_Y + REF_H - 60, PW - 2*MG, 30, NAVY)
    pt(c, PW/2, REF_Y + REF_H - 38, "[R]  REFERENCES & CONTACT", FB, 30, W, 'c')

    RCW = (PW - 2*MG - 80) * 0.68
    CCW = (PW - 2*MG - 80) * 0.30
    RX2 = MG + 30
    cx9 = MG + 30 + RCW + 50

    refs = [
        "[1] Huang R. et al. Tox21Challenge - Frontiers in Environmental Science (2016).",
        "[2] Pedregosa F. et al. Scikit-learn: Machine Learning in Python. JMLR (2011).",
        "[3] Lundberg S., Lee S. A Unified Approach to Interpreting Model Predictions. NeurIPS (2017).",
        "[4] Landrum G. et al. RDKit: Open-source cheminformatics. https://www.rdkit.org",
        "[5] Rogers D., Hahn M. Extended-Connectivity Fingerprints. J. Chem. Inf. Model. (2010).",
        "[6] McKinney W. Data Structures for Statistical Computing in Python. SciPy Proc. (2010).",
    ]
    ry2 = REF_Y + REF_H - 85
    for r in refs:
        wt(c, RX2, ry2, RCW, r, FN, 20, GRAY_D, 1.3)
        ry2 -= 42

    # Contact
    pt(c, cx9, REF_Y + REF_H - 88, "CONTACT", FB, 26, NAVY)
    hline(c, cx9, REF_Y + REF_H - 98, CCW, BLUE, 2)
    contacts = [
        ("Email :", "[prenom.nom]@etu.univh2c.ma"),
        ("GitHub:", "github.com/[username]/tox21-ml"),
        ("Univ. :", "Faculte Sciences Ben M'Sick"),
        ("Annee :", "Master Big Data S2 - 2025/2026"),
    ]
    cy8 = REF_Y + REF_H - 130
    for lbl, val in contacts:
        pt(c, cx9, cy8, lbl, FB, 21, BLUE_D)
        pt(c, cx9 + 100, cy8, val, FN, 21, GRAY_D)
        cy8 -= 42

    # ── FOOTER BAR ────────────────────────────────────────────
    fr(c, 0, 0, PW, FOOT_Y, NAVY)
    fr(c, 0, FOOT_Y - 8, PW, 8, BLUE)
    pt(c, PW/2, FOOT_Y - 55,
       "TOX21 Multi-Label ML  |  Master Data Science & Big Data  "
       "|  Faculte des Sciences Ben M'Sick  |  Universite Hassan II de Casablanca  |  2025/2026",
       FN, 22, GRAY_M, 'c')
    pt(c, PW/2, FOOT_Y - 100,
       "Random Forest  -  RDKit  -  SHAP  -  Streamlit  -  py3Dmol  -  Python 3.11",
       FI, 20, GRAY_D, 'c')

    # ── Border around whole poster ────────────────────────────
    c.setStrokeColor(NAVY)
    c.setLineWidth(6)
    c.rect(3, 3, PW - 6, PH - 6, stroke=1, fill=0)
    c.setStrokeColor(BLUE)
    c.setLineWidth(2)
    c.rect(10, 10, PW - 20, PH - 20, stroke=1, fill=0)

    c.save()
    print(f"[OK] Poster genere : {output_path}")


if __name__ == "__main__":
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Poster_TOX21_ML.pdf"
    )
    draw_poster(out)
