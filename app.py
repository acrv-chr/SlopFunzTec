import streamlit as st
import pandas as pd
import numpy as np

# Configurazione della pagina
st.set_page_config(
    page_title="Ripartizione Incentivi Tecnici",
    page_icon="💶",
    layout="wide"
)

st.title("💶 Calcolo e Ripartizione Premio Produttività (Incentivi Tecnici)")
st.caption("Distribuzione del fondo incentivi con blocco celle e auto-bilanciamento per riga")

# --- DEFINIZIONE STRUTTURA ---
RUOLI = [
    "RUP",
    "DEC",
    "Collaboratori",
    "Responsabile Fase",
    "Altri Collaboratori"
]

FASI = [
    "Programmazione della Spesa",
    "Redazione del progetto di fattibilità",
    "Gestione tecnico-amm. Progettazione",
    "Documenti di gara",
    "Gestione tecnico-amm. Affidamento",
    "Direttore esecuzione",
    "Collaudo"
]

# Matrice percentuale iniziale (somma totale = 100.0%)
DEFAULT_PCT = [
    [1.0,  0.0,  3.0,  1.0,  0.0],   # Tot: 5.0%
    [5.0,  0.0,  5.0,  2.5,  0.0],   # Tot: 12.5%
    [5.0,  0.0,  5.0,  2.5,  0.0],   # Tot: 12.5%
    [5.0,  0.0,  5.0,  2.5,  0.0],   # Tot: 12.5%
    [0.0, 12.5,  0.0,  0.0, 10.0],   # Tot: 22.5%
    [5.0,  7.5,  3.25, 1.75, 5.0],   # Tot: 22.5%
    [2.5,  0.0,  5.0,  2.5,  2.5],   # Tot: 12.5%
]

# Inizializzazione dello stato in session_state
if "matrix_pct" not in st.session_state:
    st.session_state.matrix_pct = [row.copy() for row in DEFAULT_PCT]

if "locked_cells" not in st.session_state:
    # Matrice booleana di celle bloccate (False = sbloccata)
    st.session_state.locked_cells = [[False for _ in RUOLI] for _ in FASI]

# --- CALLBACK PER AUTO-BILANCIAMENTO CON BLOCCO ---
def rebalance_row(row_idx, changed_col_idx):
    """
    Ribilancia il delta solo tra le celle non bloccate della stessa riga.
    """
    slider_key = f"slider_{row_idx}_{changed_col_idx}"
    new_val = st.session_state[slider_key]
    old_row = st.session_state.matrix_pct[row_idx]
    target_row_sum = sum(DEFAULT_PCT[row_idx])
    
    # Identifica le colonne modificabili (esclusa quella corrente e quelle bloccate)
    unlocked_cols = [
        c for c in range(len(RUOLI)) 
        if c != changed_col_idx and not st.session_state.locked_cells[row_idx][c]
    ]
    
    # Se non ci sono altre colonne sbloccate su cui distribuire, annulla il movimento
    if not unlocked_cols:
        st.session_state[slider_key] = old_row[changed_col_idx]
        st.toast(f"Tutte le altre celle della riga sono bloccate! Sblocca almeno un'altra cella.", icon="🔒")
        return

    delta = new_val - old_row[changed_col_idx]
    new_row = list(old_row)
    new_row[changed_col_idx] = new_val
    
    remaining_delta = delta
    available_indices = list(unlocked_cols)
    
    # Algoritmo di distribuzione del delta residuo
    while abs(remaining_delta) > 1e-6 and available_indices:
        split = remaining_delta / len(available_indices)
        next_available = []
        for c in available_indices:
            candidate = new_row[c] - split
            if candidate < 0.0:
                remaining_delta -= new_row[c]
                new_row[c] = 0.0
            elif candidate > target_row_sum:
                remaining_delta += (target_row_sum - new_row[c])
                new_row[c] = target_row_sum
            else:
                new_row[c] = round(candidate, 4)
                remaining_delta -= split
                next_available.append(c)
        if len(next_available) == len(available_indices):
            break
        available_indices = next_available

    # Se non è stato possibile assorbire l'intero delta (es. limiti raggiunti a 0%)
    if abs(remaining_delta) > 1e-4:
        new_row[changed_col_idx] -= remaining_delta

    # Aggiorna session_state
    for c in range(len(RUOLI)):
        st.session_state.matrix_pct[row_idx][c] = round(new_row[c], 4)
        st.session_state[f"slider_{row_idx}_{c}"] = round(new_row[c], 4)

# --- SIDEBAR: PARAMETRI GENERALI ---
with st.sidebar:
    st.header("⚙️ Parametri Progetto")
    
    valore_progetto = st.number_input(
        "Valore complessivo del progetto (€)",
        min_value=0.0,
        value=500_000.0,
        step=10_000.0,
        format="%.2f"
    )
    
    num_altri_collaboratori = st.number_input(
        "N. dipendenti struttura (Altri Collaboratori)",
        min_value=1,
        value=5,
        step=1,
        help="Numero di persone tra cui suddividere equamente l'importo della colonna 'Altri Collaboratori'"
    )
    
    st.markdown("---")
    st.subheader("Quote di Ripartizione")
    pct_fondo = st.slider("Aliquota fondo incentivante (%)", 0.0, 5.0, 2.0, 0.1) / 100.0
    pct_personale = st.slider("Quota ripartibile al personale (%)", 0.0, 100.0, 80.0, 1.0) / 100.0
    pct_innovazione = 1.0 - pct_personale

    st.markdown("---")
    if st.button("🔄 Ripristina valori e sblocca tutto"):
        st.session_state.matrix_pct = [row.copy() for row in DEFAULT_PCT]
        st.session_state.locked_cells = [[False for _ in RUOLI] for _ in FASI]
        for r in range(len(FASI)):
            for c in range(len(RUOLI)):
                st.session_state[f"slider_{r}_{c}"] = float(DEFAULT_PCT[r][c])
                st.session_state[f"lock_{r}_{c}"] = False
        st.rerun()

# --- CALCOLI FONDAMENTALI ---
fondo_totale = valore_progetto * pct_fondo
quota_distribuibile = fondo_totale * pct_personale
quota_ente = fondo_totale * pct_innovazione

# Metriche in evidenza
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Valore Progetto", f"€ {valore_progetto:,.2f}")
col_m2.metric(f"Fondo Totale ({pct_fondo*100:.1f}%)", f"€ {fondo_totale:,.2f}")
col_m3.metric(f"Quota Personale ({pct_personale*100:.0f}%)", f"€ {quota_distribuibile:,.2f}")
col_m4.metric(f"Quota Fondo Ente ({pct_innovazione*100:.0f}%)", f"€ {quota_ente:,.2f}")

st.markdown("---")

# --- REGOLAZIONE SLIDER CON BLOCCO ---
st.subheader("🎛️ Regolazione Percentuali con Blocco Celle (🔒)")
with st.expander("Apri per modificare e bloccare le percentuali", expanded=True):
    st.caption("ℹ️ Spunta **🔒 Blocca** per fissare il valore di una cella: non verrà alterata se modifichi gli altri ruoli della riga.")
    
    for i, fase in enumerate(FASI):
        row_target = sum(DEFAULT_PCT[i])
        st.markdown(f"**{i+1}. {fase}** *(Totale riga vincolato al {row_target:.2f}%)*")
        cols = st.columns(len(RUOLI))
        
        for j, ruolo in enumerate(RUOLI):
            with cols[j]:
                lock_key = f"lock_{i}_{j}"
                slider_key = f"slider_{i}_{j}"
                
                # Checkbox di blocco
                is_locked = st.checkbox(
                    "🔒 Blocca",
                    value=st.session_state.locked_cells[i][j],
                    key=lock_key,
                    help=f"Blocca {ruolo} per la fase {fase}"
                )
                st.session_state.locked_cells[i][j] = is_locked
                
                # Sincronizzazione session_state per lo slider
                if slider_key not in st.session_state:
                    st.session_state[slider_key] = float(st.session_state.matrix_pct[i][j])
                
                st.slider(
                    label=f"**{ruolo}**",
                    min_value=0.0,
                    max_value=float(row_target),
                    value=float(st.session_state.matrix_pct[i][j]),
                    step=0.25,
                    key=slider_key,
                    disabled=is_locked,
                    on_change=rebalance_row,
                    args=(i, j)
                )

df_pct = pd.DataFrame(st.session_state.matrix_pct, index=FASI, columns=RUOLI)
totale_pct = df_pct.values.sum()

if np.isclose(totale_pct, 100.0, atol=0.01):
    st.success(f" Somma totale percentuali: **{totale_pct:.2f}%** (Perfettamente bilanciata)")
else:
    st.warning(f"⚠️ Somma totale percentuali: **{totale_pct:.2f}%**")

# --- CALCOLO MATRICE ECONOMICA (€) ---
df_euro = (df_pct / 100.0) * quota_distribuibile

df_euro_display = df_euro.copy()
df_euro_display["Totale Fase (€)"] = df_euro_display.sum(axis=1)

totali_ruolo = df_euro_display.sum(axis=0)
totali_ruolo.name = "Totale Ruolo (€)"
df_euro_display = pd.concat([df_euro_display, totali_ruolo.to_frame().T])

# Formattazione per la visualizzazione
df_formatted = df_euro_display.map(lambda x: f"€ {x:,.2f}")

st.subheader("📊 Matrice Economica di Distribuzione (€)")
st.dataframe(df_formatted, use_container_width=True)

# --- FOCUS: ALTRI COLLABORATORI (TOTALE E PRO-CAPITE) ---
totale_altri_collab = totali_ruolo["Altri Collaboratori"]
quota_pro_capite = totale_altri_collab / num_altri_collaboratori if num_altri_collaboratori > 0 else 0.0

st.markdown("### 👥 Focus: Quota Pro-Capite 'Altri Collaboratori'")
col_ac1, col_ac2, col_ac3 = st.columns(3)
col_ac1.metric(
    label="Fondo Totale 'Altri Collaboratori'",
    value=f"€ {totale_altri_collab:,.2f}",
    help="Somma complessiva assegnata alla colonna Altri Collaboratori"
)
col_ac2.metric(
    label="Dipendenti Struttura Coinvolti",
    value=f"{num_altri_collaboratori}"
)
col_ac3.metric(
    label="Cifra Singolo Collaboratore",
    value=f"€ {quota_pro_capite:,.2f}",
    delta=f"{(quota_pro_capite / valore_progetto * 100):.4f}% sul progetto" if valore_progetto > 0 else None,
    help="Importo spettante a ciascun collaboratore (Totale / Numero Dipendenti)"
)

# --- QUADRO DI SINTESI PER RUOLO ---
st.markdown("---")
st.subheader("📈 Sintesi Ripartizione per Ruolo")

totali_per_ruolo_pct = df_pct.sum(axis=0)
totali_per_ruolo_eur = df_euro.sum(axis=0)

summary_df = pd.DataFrame({
    "Percentuale sul Fondo Personale (%)": totali_per_ruolo_pct.map("{:.2f}%".format),
    "Importo Spettante (€)": totali_per_ruolo_eur.map("€ {:,.2f}".format),
    "Quota sul Valore Progetto (%)": (totali_per_ruolo_eur / valore_progetto * 100).map("{:.3f}%".format) if valore_progetto > 0 else "0.000%"
})

col_tab, col_chart = st.columns([1, 1])
with col_tab:
    st.table(summary_df)

with col_chart:
    st.bar_chart(totali_per_ruolo_eur)
