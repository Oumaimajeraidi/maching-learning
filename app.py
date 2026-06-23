# -*- coding: utf-8 -*-
"""
TOX21 — Interface professionnelle + Chatbot SHAP + 3D + 2D + Historique + Dark Mode
Lancer : streamlit run app.py
"""
import os, sys, time, warnings, datetime
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import py3Dmol
import streamlit as st
import streamlit.components.v1 as components

from rdkit import Chem
from rdkit.Chem import AllChem

from src.data_preprocessing import TARGET_COLS, load_data
from src.feature_engineering import (
    featurize, get_feature_names, smiles_to_mol,
    compute_descriptors, compute_morgan_fp,
    FP_RADIUS, FP_NBITS, DESCRIPTOR_NAMES,
)
from src.predict import load_model

# ─────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TOX21 — Toxicite Moleculaire",
    page_icon="🔬",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# Theme (Light / Dark)
# ─────────────────────────────────────────────────────────────
if "dark" not in st.session_state:
    st.session_state["dark"] = False

D = st.session_state["dark"]

# Palette selon le theme
if D:
    BG        = "#0d1117"
    BG2       = "#161b22"
    BG3       = "#21262d"
    BORDER    = "#30363d"
    TXT       = "#e6edf3"
    TXT2      = "#8b949e"
    RED       = "#f85149"
    RED_BG    = "#3d1a1a"
    GREEN     = "#3fb950"
    GREEN_BG  = "#1a3d22"
    AMBER_BG  = "#3d2e0a"
    AMBER_TXT = "#e3b341"
    HEADER_G  = "linear-gradient(135deg,#010409 0%,#0d1117 60%,#161b22 100%)"
    CHAT_BG   = "#161b22"
    CHAT_BD   = "#30363d"
    BAR_BG    = "#21262d"
else:
    BG        = "#ffffff"
    BG2       = "#f8f9fa"
    BG3       = "#f0f2f5"
    BORDER    = "#e9ecef"
    TXT       = "#1a1a2e"
    TXT2      = "#868e96"
    RED       = "#c0392b"
    RED_BG    = "#fde8e8"
    GREEN     = "#27ae60"
    GREEN_BG  = "#e8f5e9"
    AMBER_BG  = "#fff8f0"
    AMBER_TXT = "#78350f"
    HEADER_G  = "linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%)"
    CHAT_BG   = "#f8f9ff"
    CHAT_BD   = "#e0e7ff"
    BAR_BG    = "#f0f2f5"

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# CSS global injecte dynamiquement
dark_overrides = f"""
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {BG} !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {"#010409" if D else "#ffffff"} !important;
    }}
    .stTextInput input, .stTextInput textarea {{
        background-color: {BG2} !important;
        color: {TXT} !important;
        border-color: {BORDER} !important;
    }}
    .stTextInput label, .stMarkdown p, .stMarkdown span,
    .stCaption, label, .stForm {{
        color: {TXT} !important;
    }}
    [data-testid="stMetric"] {{
        background: {BG2} !important;
        border: 0.5px solid {BORDER} !important;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: {TXT} !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.78rem !important;
        color: {TXT2} !important;
    }}
    .stButton > button {{
        background-color: {BG3} !important;
        color: {TXT} !important;
        border-color: {BORDER} !important;
    }}
    .stFormSubmitButton > button {{
        background-color: #1f6feb !important;
        color: white !important;
        border: none !important;
    }}
    hr {{ border-color: {BORDER} !important; }}
""" if D else ""

st.markdown(f"""
<style>
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1rem !important; padding-left: 2rem; padding-right: 2rem; }}
section[data-testid="stSidebar"] {{ width: 300px !important; }}
{dark_overrides}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Constantes & ressources
# ─────────────────────────────────────────────────────────────
MODEL_PATH   = "models/multilabel_rf_model.pkl"
DATA_PATH    = "data/tox21.csv"
N_BACKGROUND = 80
RANDOM_STATE = 42
THRESHOLD    = 0.50

TARGET_REASONS = {
    "NR-AR":         "perturbe le <b>recepteur aux androgenes</b> (hormone masculine) — risque de perturbation endocrinienne",
    "NR-AR-LBD":     "se fixe au <b>domaine de liaison du recepteur aux androgenes</b> et bloque ou active sa fonction",
    "NR-AhR":        "active le <b>recepteur AhR</b> (hydrocarbures aromatiques), implique dans la detoxification et certains cancers",
    "NR-Aromatase":  "inhibe l'<b>aromatase</b>, enzyme cle de la biosynthese des estrogenes — desequilibre hormonal possible",
    "NR-ER":         "perturbe le <b>recepteur aux estrogenes</b> — c'est un perturbateur endocrinien potentiel",
    "NR-ER-LBD":     "se lie au <b>domaine de fixation du recepteur aux estrogenes</b> et module son activite",
    "NR-PPAR-gamma": "active <b>PPAR-gamma</b>, recepteur lie au metabolisme lipidique et au diabete de type 2",
    "SR-ARE":        "declenche une <b>reponse au stress oxydatif</b> (voie ARE) — desequilibre redox cellulaire",
    "SR-ATAD5":      "cause des <b>dommages a l'ADN</b> detectes par le systeme ATAD5 — risque genotoxique",
    "SR-HSE":        "induit un <b>stress thermique</b> (choc thermique) — dysfonction des proteines cellulaires",
    "SR-MMP":        "perturbe le <b>potentiel de la membrane mitochondriale</b> — dysfonction energetique et apoptose",
    "SR-p53":        "active la <b>voie p53</b>, gardien du genome — signal de dommages ADN pouvant mener au cancer",
}
FEATURE_LABELS = {
    "MolWt":"Poids moleculaire","LogP":"Lipophilicite (LogP)","TPSA":"Surface polaire (TPSA)",
    "NumAtoms":"Nombre d'atomes","NumBonds":"Nombre de liaisons","HBondDonors":"Donneurs liaisons H",
    "HBondAcceptors":"Accepteurs liaisons H","RotatableBonds":"Liaisons rotatives",
    "AromaticRings":"Cycles aromatiques","FractionCSP3":"Fraction sp3",
    "HeavyAtomCount":"Atomes lourds","NumRings":"Nombre de cycles",
    "NumHeteroatoms":"Heteroatomes (N,O,S...)","NumAliphaticRings":"Cycles aliphatiques",
    "MolMR":"Refractivite molaire",
}

@st.cache_resource(show_spinner="Chargement du modele TOX21...")
def load_resources():
    pkg = load_model(MODEL_PATH)
    df  = load_data(DATA_PATH).dropna(subset=TARGET_COLS)
    X_all, _, _ = featurize(df["smiles"].tolist())
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X_all), min(N_BACKGROUND, len(X_all)), replace=False)
    return pkg, X_all[idx].astype(np.float64), get_feature_names()

pkg, background, feat_names = load_resources()

# ─────────────────────────────────────────────────────────────
# Historique
# ─────────────────────────────────────────────────────────────
def add_to_history(smiles, n_toxic, max_score, max_label):
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if any(h["smiles"] == smiles for h in st.session_state["history"]):
        return
    st.session_state["history"].insert(0, {
        "smiles": smiles, "n_toxic": n_toxic,
        "max_score": round(max_score, 3), "max_label": max_label,
        "heure": datetime.datetime.now().strftime("%H:%M"),
    })
    st.session_state["history"] = st.session_state["history"][:15]

# ─────────────────────────────────────────────────────────────
# Structure 3D
# ─────────────────────────────────────────────────────────────
def make_3d_html(smiles: str, width=500, height=300) -> str:
    mol = smiles_to_mol(smiles)
    if mol is None:
        return ""
    try:
        mol_h  = Chem.AddHs(mol)
        params = AllChem.ETKDGv3(); params.randomSeed = 42
        ok = AllChem.EmbedMolecule(mol_h, params)
        if ok == 0:
            AllChem.MMFFOptimizeMolecule(mol_h, maxIters=500)
            mol_3d = mol_h
        else:
            ok2 = AllChem.EmbedMolecule(mol, params)
            if ok2 == -1: return ""
            mol_3d = mol
        sdf    = Chem.MolToMolBlock(mol_3d)
        sdf_js = sdf.replace("\\","\\\\").replace("'","\\'").replace("\n","\\n").replace("\r","")
        viewer_bg = "#0d1117" if D else "#f8f9fa"
        toolbar_bg = "#161b22" if D else "#ffffff"
        toolbar_bd = "#30363d" if D else "#e9ecef"
        btn_bg     = "#21262d" if D else "#f0f2f5"
        btn_color  = "#e6edf3" if D else "#343a40"
        tip_color  = "#6e7681" if D else "#868e96"
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.4/jquery.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/3dmol@2.0.1/build/3Dmol-min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:transparent;font-family:{FONT};}}
#vwrap{{border:1px solid {toolbar_bd};border-radius:14px;overflow:hidden;}}
#mol3d{{width:{width}px;height:{height}px;position:relative;}}
.bar{{padding:7px 12px;background:{toolbar_bg};border-top:1px solid {toolbar_bd};
      display:flex;gap:8px;align-items:center;flex-wrap:wrap;}}
.btn{{background:{btn_bg};border:1px solid {toolbar_bd};border-radius:6px;
      color:{btn_color};font-size:11px;padding:3px 9px;cursor:pointer;}}
.btn:hover{{opacity:0.8;}}
.tip{{font-size:10px;color:{tip_color};margin-left:auto;}}
</style></head>
<body>
<div id="vwrap">
  <div id="mol3d"></div>
  <div class="bar">
    <button class="btn" onclick="toggleSpin()">⏸ Pause</button>
    <button class="btn" onclick="setBS()">Boules & Batons</button>
    <button class="btn" onclick="setStick()">Batons</button>
    <button class="btn" onclick="setSphere()">Spheres</button>
    <span class="tip">🖱 Gauche: rotation | Molette: zoom</span>
  </div>
</div>
<script>
var vw, spin=true;
$(function(){{
  vw=$3Dmol.createViewer($('#mol3d'),{{backgroundColor:'{viewer_bg}'}});
  vw.addModel('{sdf_js}','sdf');
  vw.setStyle({{}},{{stick:{{colorscheme:'Jmol',radius:0.12}},sphere:{{colorscheme:'Jmol',scale:0.28}}}});
  vw.zoomTo(); vw.spin('y',0.8); vw.render();
}});
function toggleSpin(){{spin?vw.spin(false):vw.spin('y',0.8);spin=!spin;}}
function setBS(){{vw.setStyle({{}},{{stick:{{colorscheme:'Jmol',radius:0.12}},sphere:{{colorscheme:'Jmol',scale:0.28}}}});vw.render();}}
function setStick(){{vw.setStyle({{}},{{stick:{{colorscheme:'Jmol',radius:0.15}}}});vw.render();}}
function setSphere(){{vw.setStyle({{}},{{sphere:{{colorscheme:'Jmol',scale:0.4}}}});vw.render();}}
</script></body></html>"""
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────
# Metier : prediction + SHAP
# ─────────────────────────────────────────────────────────────
def predict_molecule(smiles):
    mol = smiles_to_mol(smiles)
    if mol is None: return None,None,None,None
    desc = compute_descriptors(mol)
    if desc is None: return None,None,None,None
    fp    = compute_morgan_fp(mol)
    X     = np.hstack([desc,fp]).reshape(1,-1).astype(np.float32)
    proba = np.array([e.predict_proba(X)[0,1] for e in pkg["model"].estimators_])
    pred  = (proba>=THRESHOLD).astype(int)
    return proba, pred, dict(zip(DESCRIPTOR_NAMES,desc)), mol

def compute_shap(smiles, target_idx):
    mol=smiles_to_mol(smiles); desc=compute_descriptors(mol); fp=compute_morgan_fp(mol)
    X=np.hstack([desc,fp]).reshape(1,-1).astype(np.float64)
    est=pkg["model"].estimators_[target_idx]
    try:
        ex=shap.TreeExplainer(est,data=background,feature_perturbation="interventional")
        sv=ex.shap_values(X,check_additivity=False)
        if isinstance(sv,list) and len(sv)==2: sv=np.array(sv[1])
        elif isinstance(sv,np.ndarray) and sv.ndim==3: sv=sv[:,:,1]
        else:
            sv=np.array(sv)
            if sv.ndim==3: sv=sv[:,:,1]
        return sv.reshape(X.shape[0],-1)[0]
    except: return None

def describe_feature(name, val):
    if name=="LogP":
        return (f"tres lipophile (LogP={val:.2f}) — traverse facilement les membranes" if val>4
                else f"moderement lipophile (LogP={val:.2f})" if val>2
                else f"hydrophile (LogP={val:.2f})")
    if name=="MolWt":
        return (f"poids eleve ({val:.0f} g/mol) — accumulation tissulaire possible" if val>450
                else f"poids modere ({val:.0f} g/mol)")
    if name=="TPSA":
        return (f"surface polaire faible (TPSA={val:.0f} A2) — penetration membranaire maximale" if val<40
                else f"surface polaire elevee (TPSA={val:.0f} A2)" if val>=90
                else f"surface polaire moderee (TPSA={val:.0f} A2)")
    if name=="AromaticRings":
        return (f"{int(val)} cycles aromatiques — risque d'intercalation dans l'ADN" if val>=3
                else f"{int(val)} cycle(s) aromatique(s)")
    if name=="NumHeteroatoms":
        return f"{int(val)} heteroatome(s) — points d'interaction specifiques" if val>=4 else f"{int(val)} heteroatome(s)"
    if name=="HBondDonors":
        return f"{int(val)} donneurs liaisons H — interactions fortes avec les recepteurs" if val>=3 else f"{int(val)} donneur(s)"
    if name=="FractionCSP3":
        return (f"molecule plane ({val:.2f}) — typique des molecules aromatiques actives" if val<0.2
                else f"forte composante 3D ({val:.2f})" if val>0.6 else f"FractionCSP3={val:.2f}")
    return f"{FEATURE_LABELS.get(name,name)} = {val:.2f}"

def make_shap_figure(sv, target_name):
    df_s  = pd.DataFrame({"feature":feat_names,"shap":sv})
    top10 = df_s.reindex(df_s["shap"].abs().nlargest(10).index).sort_values("shap")
    top10["label"] = top10["feature"].map(lambda f: FEATURE_LABELS.get(f,f))
    fig_bg = BG2; ax_bg = BG2; txt_c = TXT; grid_c = BORDER
    fig, ax = plt.subplots(figsize=(7.5,4))
    fig.patch.set_facecolor(fig_bg)
    ax.set_facecolor(ax_bg)
    colors = [RED if v>0 else GREEN for v in top10["shap"]]
    ax.barh(top10["label"],top10["shap"],color=colors,edgecolor="none",height=0.6)
    ax.axvline(0,color=grid_c,linewidth=0.8,ls="--")
    ax.set_xlabel("Valeur SHAP  (rouge=toxicite | vert=protection)",fontsize=9,color=txt_c)
    ax.set_title(f"Proprietes chimiques expliquant {target_name}",fontsize=10.5,fontweight="bold",pad=12,color=txt_c)
    ax.tick_params(axis="y",labelsize=9,colors=txt_c)
    ax.tick_params(axis="x",colors=txt_c)
    ax.spines[["top","right"]].set_visible(False)
    for spine in ["bottom","left"]: ax.spines[spine].set_color(BORDER)
    plt.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────
# HTML composants (theme-aware)
# ─────────────────────────────────────────────────────────────
def html_results_table(labels, proba, pred):
    rows=""
    for i,lbl in enumerate(labels):
        p=float(proba[i]); toxic=bool(pred[i]); pct=int(p*100)
        bc=RED if toxic else GREEN
        bb=RED_BG; bf=RED if toxic else GREEN
        bt="TOXIQUE" if toxic else "non"
        nw="700" if toxic else "400"
        dot=RED if toxic else BORDER
        rows+=f"""
        <div style="padding:10px 0;border-bottom:1px solid {BORDER};">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:8px;height:8px;border-radius:50%;background:{dot};flex-shrink:0;"></div>
              <span style="font-size:14px;font-weight:{nw};color:{TXT};font-family:{FONT};">{lbl}</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:13px;color:{TXT2};font-variant-numeric:tabular-nums;">{p:.3f}</span>
              <span style="background:{RED_BG if toxic else GREEN_BG};color:{bf};font-size:11px;
                           font-weight:700;padding:3px 10px;border-radius:99px;">{bt}</span>
            </div>
          </div>
          <div style="background:{BAR_BG};height:7px;border-radius:99px;overflow:hidden;">
            <div style="background:{bc};height:7px;width:{pct}%;border-radius:99px;"></div>
          </div>
        </div>"""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;margin:0;padding:0;}}</style></head>
    <body style="background:transparent;font-family:{FONT};">
    <div style="background:{BG2};border:1px solid {BORDER};border-radius:14px;padding:20px 24px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <p style="font-size:15px;font-weight:700;color:{TXT};">Resultats par cible</p>
        <span style="font-size:12px;color:{TXT2};background:{BG3};
                     padding:4px 10px;border-radius:99px;border:1px solid {BORDER};">Seuil = 0.50</span>
      </div>
      {rows}
    </div></body></html>"""

def html_chat_bubble(text_html):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>*{{box-sizing:border-box;margin:0;padding:0;}}</style></head>
    <body style="background:transparent;font-family:{FONT};">
    <div style="display:flex;gap:14px;align-items:flex-start;">
      <div style="flex-shrink:0;width:42px;height:42px;border-radius:50%;
                  background:linear-gradient(135deg,#667eea,#764ba2);
                  display:flex;align-items:center;justify-content:center;font-size:1.3rem;">🤖</div>
      <div style="flex:1;background:{CHAT_BG};border:1px solid {CHAT_BD};
                  border-radius:0 14px 14px 14px;padding:18px 20px;
                  font-size:14px;line-height:1.8;color:{TXT};">
        {text_html}
      </div>
    </div></body></html>"""

def build_explanation_html(proba, pred, desc_vals, sv, labels):
    n_toxic    = int(pred.sum())
    toxic_list = [(labels[i],float(proba[i])) for i in range(len(labels)) if pred[i]==1]
    toxic_list.sort(key=lambda x:-x[1])
    main_tgt   = toxic_list[0][0] if toxic_list else labels[int(np.argmax(proba))]
    parts=[]
    if n_toxic==0:
        top_i=int(np.argmax(proba))
        parts.append(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <span style="font-size:1.3rem;">✅</span>
          <strong style="color:{GREEN};">Aucune toxicite predite</strong>
        </div>
        <p style="color:{TXT};">Cette molecule <strong>n'est pas toxique</strong> pour aucune des 12 cibles TOX21.
        Score le plus eleve : <strong>{labels[top_i]}</strong> ({float(proba[top_i]):.1%}) — sous le seuil de 50%.</p>
        <p style="margin-top:10px;font-size:12px;color:{TXT2};"><em>Rappel : absence de toxicite predite
        ne garantit pas l'innocuite absolue.</em></p>""")
        return "\n".join(parts), None

    icon_v="⚠️" if n_toxic==1 else "🚨"
    label_v=f"{n_toxic} cible{'s' if n_toxic>1 else ''} toxique{'s' if n_toxic>1 else ''}"
    parts.append(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span style="font-size:1.3rem;">{icon_v}</span>
      <strong style="color:{RED};">Molecule toxique — {label_v}</strong>
    </div>""")
    bullets=""
    for tgt,prob in toxic_list:
        reason=TARGET_REASONS.get(tgt,"mecanisme non repertorie")
        bullets+=f"""
        <div style="display:flex;gap:8px;margin-bottom:9px;align-items:flex-start;">
          <span style="color:{RED};font-weight:700;flex-shrink:0;margin-top:2px;">•</span>
          <span style="color:{TXT};"><strong style="color:{RED};">{tgt}</strong>
          <span style="background:{RED_BG};color:{RED};font-size:11px;font-weight:700;
                       padding:1px 7px;border-radius:99px;margin:0 6px;">{prob:.1%}</span>
          — elle {reason}.</span>
        </div>"""
    parts.append(f'<div style="margin-bottom:14px;">{bullets}</div>')
    parts.append(f"""
    <div style="border-top:1px solid {BORDER};margin:14px 0;"></div>
    <p style="font-size:13px;font-weight:700;color:{TXT};margin-bottom:10px;">
      Pourquoi <span style="color:{RED};">{main_tgt}</span> ? — Explication chimique
    </p>""")
    if sv is not None:
        desc_pos={DESCRIPTOR_NAMES[i]:sv[i] for i in range(len(DESCRIPTOR_NAMES)) if sv[i]>0}
        desc_pos=dict(sorted(desc_pos.items(),key=lambda x:-x[1]))
        if desc_pos:
            items_html=""
            for rank,(fname,_) in enumerate(list(desc_pos.items())[:4],1):
                val=desc_vals.get(fname,0.0); expl=describe_feature(fname,val)
                items_html+=f"""
                <div style="display:flex;gap:10px;margin-bottom:9px;align-items:flex-start;">
                  <div style="background:{RED};color:white;border-radius:50%;width:22px;height:22px;
                               display:flex;align-items:center;justify-content:center;
                               font-size:11px;font-weight:700;flex-shrink:0;">{rank}</div>
                  <div>
                    <strong style="color:{TXT};">{FEATURE_LABELS.get(fname,fname)}</strong><br>
                    <span style="color:{TXT2};font-size:13px;">{expl}</span>
                  </div>
                </div>"""
            parts.append(f'<div style="margin-bottom:12px;">{items_html}</div>')
        n_fp_pos=int((sv[len(DESCRIPTOR_NAMES):]>0).sum())
        if n_fp_pos>0:
            parts.append(f"""
            <div style="background:{AMBER_BG};border:1px solid {AMBER_TXT};border-radius:8px;
                        padding:10px 14px;margin-bottom:12px;font-size:13px;color:{AMBER_TXT};">
              &#9432; <strong>{n_fp_pos} sous-structures moleculaires</strong> caracteristiques
              des molecules toxiques pour {main_tgt}.
            </div>""")
        desc_neg={DESCRIPTOR_NAMES[i]:sv[i] for i in range(len(DESCRIPTOR_NAMES)) if sv[i]<-0.003}
        if desc_neg:
            bp=min(desc_neg,key=desc_neg.get); val=desc_vals.get(bp,0.0)
            parts.append(f"""
            <div style="background:{GREEN_BG};border:1px solid {GREEN};border-radius:8px;
                        padding:10px 14px;margin-bottom:12px;font-size:13px;color:{GREEN};">
              &#10003; <strong>Facteur protecteur :</strong> {FEATURE_LABELS.get(bp,bp)}
              ({val:.2f}) tend a reduire le risque de toxicite.
            </div>""")
    else:
        parts.append(f"<p style='color:{TXT2};font-size:13px;'><em>(Explication SHAP non disponible)</em></p>")
    parts.append(f"""
    <div style="border-top:1px solid {BORDER};margin-top:14px;padding-top:10px;
                font-size:11px;color:{TXT2};">
      Modele : Random Forest multi-label (200 arbres x 12 cibles) &nbsp;•&nbsp;
      AUC-ROC macro = {pkg['metrics']['auc_macro']} &nbsp;•&nbsp;
      Ces predictions ne remplacent pas des tests biologiques.
    </div>""")
    return "\n".join(parts), main_tgt

# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Logo + toggle dark mode
        col_logo, col_toggle = st.columns([3, 1])
        with col_logo:
            st.markdown(f"""
            <div style="padding:0.8rem 0 0.3rem;">
              <span style="font-size:1.6rem;">🔬</span>
              <span style="font-size:1rem;font-weight:700;color:{TXT};margin-left:6px;">TOX21</span>
              <p style="font-size:0.72rem;color:{TXT2};margin:2px 0 0;">Prediction de toxicite</p>
            </div>""", unsafe_allow_html=True)
        with col_toggle:
            st.markdown("<div style='padding-top:0.9rem;'>", unsafe_allow_html=True)
            icon = "☀️" if D else "🌙"
            if st.button(icon, key="dark_toggle", help="Basculer Dark / Light mode"):
                st.session_state["dark"] = not st.session_state["dark"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<hr style='border:0.5px solid {BORDER};margin:0.5rem 0;'>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:13px;font-weight:700;color:{TXT};margin-bottom:8px;'>📋 Historique des analyses</p>", unsafe_allow_html=True)

        history = st.session_state.get("history", [])
        if not history:
            st.markdown(f"""
            <div style="background:{BG2};border-radius:10px;padding:1rem;text-align:center;
                        color:{TXT2};font-size:0.82rem;">
              Aucune analyse effectuee.<br>Analysez une molecule pour la voir ici.
            </div>""", unsafe_allow_html=True)
        else:
            for i, item in enumerate(history):
                toxic     = item["n_toxic"] > 0
                dot_color = RED if toxic else GREEN
                label_tx  = (f"<span style='color:{RED};font-weight:700;'>{item['n_toxic']}/12 TOXIQUE</span>"
                             if toxic else f"<span style='color:{GREEN};'>0/12 — non toxique</span>")
                smi_short = item["smiles"][:22]+"..." if len(item["smiles"])>22 else item["smiles"]
                st.markdown(f"""
                <div style="background:{BG2};border:0.5px solid {BORDER};border-radius:10px;
                             padding:10px 12px;margin-bottom:8px;">
                  <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <div style="width:8px;height:8px;border-radius:50%;background:{dot_color};"></div>
                    <span style="font-size:12px;font-weight:600;color:{TXT};font-family:monospace;">{smi_short}</span>
                  </div>
                  <div style="font-size:11px;margin-bottom:2px;">{label_tx}</div>
                  <div style="font-size:11px;color:{TXT2};">Score : {item['max_score']} ({item['max_label']}) • {item['heure']}</div>
                </div>""", unsafe_allow_html=True)
                if st.button("↑ Recharger", key=f"h_{i}", use_container_width=True):
                    st.session_state["smiles_val"] = item["smiles"]
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Vider l'historique", use_container_width=True):
                st.session_state["history"] = []
                st.rerun()

        st.markdown(f"""
        <hr style="border:0.5px solid {BORDER};margin:1rem 0;">
        <div style="font-size:11px;color:{TXT2};text-align:center;line-height:1.6;">
          Random Forest • 200 arbres • 12 cibles<br>AUC-ROC macro = 0.783
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
render_sidebar()

# En-tete
st.markdown(f"""
<div style="background:{HEADER_G};border-radius:16px;padding:22px 28px 18px;margin-bottom:1.2rem;">
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="font-size:2rem;">🔬</span>
    <div>
      <h1 style="margin:0;font-size:1.5rem;font-weight:700;color:white;letter-spacing:-0.3px;">
        TOX21 — Prediction de Toxicite Moleculaire
      </h1>
      <p style="margin:4px 0 0;font-size:0.85rem;color:#8892b0;">
        IA • 12 Cibles Biologiques • SHAP • Structure 2D/3D • {"🌙 Mode Sombre" if D else "☀️ Mode Clair"}
      </p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Exemples
st.markdown(f"<p style='color:{TXT};font-weight:500;'>Exemples rapides :</p>", unsafe_allow_html=True)
ex_cols = st.columns(4)
for col, (name, smi) in zip(ex_cols, {
    "Bisphenol A":"CC(c1ccc(O)cc1)(c1ccc(O)cc1)C",
    "Dioxine":    "Clc1cc2c(cc1Cl)Oc1c(Cl)c(Cl)ccc1O2",
    "Aspirine":   "CC(=O)Oc1ccccc1C(=O)O",
    "Ethanol":    "CCO",
}.items()):
    if col.button(name, use_container_width=True):
        st.session_state["smiles_val"] = smi

st.markdown("<br>", unsafe_allow_html=True)

with st.form("main_form", clear_on_submit=False):
    smiles_input = st.text_input(
        "Entrer un SMILES de molecule",
        value=st.session_state.get("smiles_val",""),
        placeholder="ex: CC(=O)Oc1ccccc1C(=O)O",
    )
    clicked = st.form_submit_button("🔬  Analyser la Molecule", use_container_width=True, type="primary")

# ─────────────────────────────────────────────────────────────
# Resultats
# ─────────────────────────────────────────────────────────────
if clicked and smiles_input.strip():
    smiles = smiles_input.strip()
    st.session_state["smiles_val"] = smiles

    with st.spinner("Analyse moleculaire..."):
        proba, pred, desc_vals, mol = predict_molecule(smiles)

    if proba is None:
        st.error("SMILES invalide — verifiez la syntaxe (ex: CCO pour l'ethanol).")
        st.stop()

    labels  = pkg["targets"]
    n_toxic = int(pred.sum())
    max_idx = int(np.argmax(proba))
    max_lbl = labels[max_idx]; max_prob = float(proba[max_idx])
    toxic_idxs   = [i for i in range(len(labels)) if pred[i]==1]
    main_tgt_idx = int(toxic_idxs[int(np.argmax(proba[toxic_idxs]))]) if toxic_idxs else max_idx

    add_to_history(smiles, n_toxic, max_prob, max_lbl)

    st.markdown("---")

    # ── 2 colonnes : scores/tableau | 3D ─────────────────────
    col_scores, col_3d = st.columns([1.1, 1.1], gap="medium")

    with col_scores:
        m1,m2,m3 = st.columns(3)
        m1.metric("Cibles toxiques", str(n_toxic),
                  "sur 12" if n_toxic>0 else "Aucune",
                  delta_color="inverse" if n_toxic>0 else "normal")
        m2.metric("Cibles testees", "12")
        m3.metric("Score max", f"{max_prob:.3f}",
                  "TOXIQUE" if max_prob>=THRESHOLD else "sous seuil",
                  delta_color="inverse" if max_prob>=THRESHOLD else "normal")
        st.markdown("<br>", unsafe_allow_html=True)
        components.html(html_results_table(labels,proba,pred),
                        height=len(labels)*62+90, scrolling=False)

    with col_3d:
        st.markdown(f"<p style='font-size:14px;font-weight:700;color:{TXT};margin-bottom:6px;'>🧬 Structure 3D interactive</p>",
                    unsafe_allow_html=True)
        with st.spinner("Generation 3D..."):
            html3d = make_3d_html(smiles, width=500, height=320)
        if html3d:
            components.html(html3d, height=390, scrolling=False)
            st.caption("C=gris | O=rouge | N=bleu | H=blanc | Cl=vert | S=jaune")
        else:
            st.info("Structure 3D non disponible.")

    # ── Chatbot SHAP ──────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"<h3 style='color:{TXT};'>🤖 Explication par Intelligence Artificielle</h3>",
                unsafe_allow_html=True)
    st.caption("Analyse des proprietes chimiques — pourquoi cette molecule est (ou n'est pas) toxique")

    with st.spinner("Calcul SHAP..."):
        sv  = compute_shap(smiles, main_tgt_idx)
        fig = make_shap_figure(sv, labels[main_tgt_idx]) if sv is not None else None

    expl_html, main_tgt = build_explanation_html(proba, pred, desc_vals, sv, labels)

    words = expl_html.split(" ")
    placeholder = st.empty()
    displayed = ""
    for i, word in enumerate(words):
        displayed += word + " "
        if i % 25 == 0 or i == len(words)-1:
            placeholder.empty()
            with placeholder.container():
                components.html(html_chat_bubble(displayed), height=500, scrolling=True)
            time.sleep(0.03)

    placeholder.empty()
    components.html(html_chat_bubble(expl_html), height=500, scrolling=True)

    if fig is not None:
        st.markdown(f"<p style='font-weight:700;color:{TXT};'>Graphique SHAP :</p>", unsafe_allow_html=True)
        st.pyplot(fig, use_container_width=True)

elif clicked:
    st.warning("Entrez un SMILES avant de cliquer sur Analyser.")
