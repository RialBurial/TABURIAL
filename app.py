import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Trading MTFA Scanner PRO", layout="wide")

# Configuración de activos (Tickers de Yahoo Finance)
TICKERS = {
    "S&P 500": "ES=F",       # Futuros S&P 500
    "Nasdaq": "NQ=F",        # Futuros Nasdaq
    "Oil": "CL=F",           # Futuros Crude Oil
    "Gasoil": "HO=F",        # Futuros Heating Oil
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X"
}

TEMPORALIDADES = {
    "Mensual": 8.0,
    "Semanal": 5.0,
    "Diario": 3.0,
    "4 Horas": 2.0,
    "1 Hora": 1.0,
    "30 Minutos": 0.5,
    "15 Minutos": 0.25,
    "5 Minutos": 0.25
}
MAX_PUNTOS = sum(TEMPORALIDADES.values()) # 20.0

# Mapeo de temporalidades para yfinance: (periodo a descargar, intervalo)
YF_MAP = {
    "Mensual": ("10y", "1mo"),
    "Semanal": ("2y", "1wk"),
    "Diario": ("1y", "1d"),
    "4 Horas": ("1mo", "1h"), # Se descargará 1h y se re-muestreará a 4h
    "1 Hora": ("1mo", "1h"),
    "30 Minutos": ("5d", "30m"),
    "15 Minutos": ("5d", "15m"),
    "5 Minutos": ("1d", "5m")
}

@st.cache_data(ttl=300, show_spinner=False) # Caché de 5 minutos para no saturar la red
def evaluar_algoritmo(activo, tf_name):
    ticker = TICKERS[activo]
    period, interval = YF_MAP[tf_name]
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty: return 0
        
        # yfinance no tiene 4h nativo, así que agrupamos velas de 1h
        if tf_name == "4 Horas":
            df = df.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
            
        if len(df) < 50: return 0 # No hay datos suficientes para la SMA de 50
        
        # Asegurar que tomamos solo la columna Close (a veces YF devuelve MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            close = df['Close'].iloc[:, 0]
        else:
            close = df['Close']
            
        ema20 = close.ewm(span=20, adjust=False).mean()
        sma50 = close.rolling(window=50).mean()
        
        last_close = float(close.iloc[-1])
        last_ema = float(ema20.iloc[-1])
        last_sma = float(sma50.iloc[-1])
        
        if last_close > last_ema and last_ema > last_sma:
            return 1 # Alcista
        elif last_close < last_ema and last_ema < last_sma:
            return -1 # Bajista
        else:
            return 0 # Lateral
            
    except Exception as e:
        return 0 # En caso de error de conexión, marcamos neutral

st.title("📊 MTFA Scanner: Humano vs Máquina")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    activo_actual = st.selectbox("Selecciona el activo:", list(TICKERS.keys()))
    st.markdown("---")
    st.write("Columna Izquierda: Tu análisis manual.")
    st.write("Columna Central: Análisis Automático (EMA 20 / SMA 50).")

# Estado
if 'evaluaciones' not in st.session_state:
    st.session_state['evaluaciones'] = {}

if activo_actual not in st.session_state['evaluaciones']:
    st.session_state['evaluaciones'][activo_actual] = {tf: 0 for tf in TEMPORALIDADES.keys()}

opciones = {"Alcista 🟢": 1, "Lateral ⚪": 0, "Bajista 🔴": -1}
opciones_inversas = {1: "Alcista 🟢", 0: "Lateral ⚪", -1: "Bajista 🔴"}

puntuacion_manual = 0.0
puntuacion_auto = 0.0

st.markdown(f"### Análisis de **{activo_actual}**")

# Botón para forzar actualización de datos
col_header1, col_header2 = st.columns([3, 1])
with col_header2:
    if st.button("🔄 Actualizar Datos Algoritmo"):
        evaluar_algoritmo.clear()

st.divider()

# Tres columnas: Manual, Auto, Termómetros
col_man, col_aut, col_term = st.columns([1.5, 1.2, 1.5])

with col_man:
    st.subheader("🧠 Tu Análisis (Manual)")
    st.write("Registra tu visión del precio.")
    for tf, peso in TEMPORALIDADES.items():
        valor_actual = st.session_state['evaluaciones'][activo_actual][tf]
        
        seleccion = st.radio(
            f"**{tf}** (Peso: {peso})",
            options=list(opciones.keys()),
            index=list(opciones.keys()).index(opciones_inversas[valor_actual]),
            horizontal=True,
            key=f"radio_{activo_actual}_{tf}"
        )
        
        valor_numerico = opciones[seleccion]
        st.session_state['evaluaciones'][activo_actual][tf] = valor_numerico
        puntuacion_manual += valor_numerico * peso

with col_aut:
    st.subheader("🤖 Algoritmo (EMA20/50)")
    st.write("Datos reales en vivo.")
    
    with st.spinner("Calculando medias..."):
        for tf, peso in TEMPORALIDADES.items():
            # Llamada al algoritmo
            valor_auto = evaluar_algoritmo(activo_actual, tf)
            puntuacion_auto += valor_auto * peso
            
            # Formato visual
            if valor_auto == 1:
                etiqueta = "🟢 **Alcista**"
            elif valor_auto == -1:
                etiqueta = "🔴 **Bajista**"
            else:
                etiqueta = "⚪ **Lateral**"
                
            # Usamos markdown con algo de padding para alinear visualmente con la botonera manual
            st.markdown(f"<div style='padding-top: 15px; padding-bottom: 23px;'>{etiqueta}</div>", unsafe_allow_html=True)


# Función auxiliar para renderizar termómetros
def dibujar_termometro(puntuacion, titulo):
    porcentaje = (puntuacion / MAX_PUNTOS) * 100
    if porcentaje >= 75: zona, color = "Fuerte Compras", "#00c853"
    elif porcentaje >= 25: zona, color = "Mod. Alcista", "#81c784"
    elif porcentaje > -25: zona, color = "Lateral (No Operar)", "#9e9e9e"
    elif porcentaje > -75: zona, color = "Mod. Bajista", "#e57373"
    else: zona, color = "Fuerte Ventas", "#d50000"
    
    porcentaje_visual = (porcentaje + 100) / 2
    
    st.markdown(f"**{titulo}** ({porcentaje:.1f}%)")
    st.markdown(f"""
    <div style="width: 100%; background-color: #2b2b2b; border-radius: 5px; height: 25px; margin-bottom: 5px; border: 1px solid #555;">
        <div style="width: {porcentaje_visual}%; background-color: {color}; height: 100%; border-radius: 4px; transition: width 0.5s ease-in-out;"></div>
    </div>
    <div style="text-align: center; padding: 5px; border-radius: 5px; background-color: {color}20; border: 1px solid {color}; margin-bottom: 20px;">
        <span style="color: {color}; font-weight: bold;">{zona}</span>
    </div>
    """, unsafe_allow_html=True)

with col_term:
    st.subheader("⚖️ Veredicto Global")
    st.write("Compara los sesgos.")
    
    dibujar_termometro(puntuacion_manual, "🧠 Sesgo Manual")
    dibujar_termometro(puntuacion_auto, "🤖 Sesgo Algoritmo")
    
    # Análisis de discrepancia
    diferencia = abs(puntuacion_manual - puntuacion_auto)
    st.divider()
    if diferencia == 0:
        st.success("✅ **Sincronización Perfecta:** Tu lectura del mercado es idéntica a la matemática pura.")
    elif diferencia <= 5:
        st.info("⚠️ **Desviación Leve:** Estás leyendo bien el contexto, pero hay ruido en las temporalidades menores.")
    else:
        st.error("🚨 **Alerta de Autosabotaje:** Tu sesgo manual difiere drásticamente de la tendencia algorítmica real. Revisa tus gráficos.")
