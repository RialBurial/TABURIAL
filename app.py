import streamlit as st

st.set_page_config(page_title="Trading MTFA Scanner", layout="wide")

# Configuración de activos y temporalidades
ACTIVOS = ["S&P 500", "Nasdaq", "Oil", "Gasoil", "EUR/USD", "GBP/USD"]
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

st.title("📊 Escáner Direccional MTFA (Top-Down)")

# Selector de activo principal en la barra lateral
with st.sidebar:
    st.header("Configuración")
    activo_actual = st.selectbox("Selecciona el activo a evaluar:", ACTIVOS)
    st.markdown("---")
    st.write("Selecciona el sesgo en la pantalla principal. El sistema calculará el peso de cada temporalidad basado en Fibonacci.")

# Inicializar el estado de las evaluaciones si no existe
if 'evaluaciones' not in st.session_state:
    st.session_state['evaluaciones'] = {}

if activo_actual not in st.session_state['evaluaciones']:
    st.session_state['evaluaciones'][activo_actual] = {tf: 0 for tf in TEMPORALIDADES.keys()}

# Opciones de la botonera
opciones = {"Alcista 🟢": 1, "Lateral ⚪": 0, "Bajista 🔴": -1}
opciones_inversas = {1: "Alcista 🟢", 0: "Lateral ⚪", -1: "Bajista 🔴"}

puntuacion_total = 0.0

# Interfaz principal
st.markdown(f"### Ficha de Evaluación: **{activo_actual}**")

col1, col2 = st.columns([2, 1.5])

with col1:
    st.markdown("#### Temporalidades")
    for tf, peso in TEMPORALIDADES.items():
        # Obtener valor actual del estado
        valor_actual = st.session_state['evaluaciones'][activo_actual][tf]
        label_actual = opciones_inversas[valor_actual]
        
        # Crear la botonera (Radio horizontal)
        seleccion = st.radio(
            f"**{tf}** (Peso: {peso})",
            options=list(opciones.keys()),
            index=list(opciones.keys()).index(label_actual),
            horizontal=True,
            key=f"radio_{activo_actual}_{tf}"
        )
        
        # Actualizar el estado
        valor_numerico = opciones[seleccion]
        st.session_state['evaluaciones'][activo_actual][tf] = valor_numerico
        
        # Sumar a puntuación total
        puntuacion_total += valor_numerico * peso

# Calcular porcentaje (-100% a +100%)
porcentaje = (puntuacion_total / MAX_PUNTOS) * 100

# Determinar zona y color del termómetro
if porcentaje >= 75:
    zona = "Tendencia Alcista Fuerte (Buscar Compras)"
    color = "#00c853" # Verde fuerte
elif porcentaje >= 25:
    zona = "Alcista Moderado / Retroceso"
    color = "#81c784" # Verde claro
elif porcentaje > -25:
    zona = "Zona Lateral / Conflicto (No Operar)"
    color = "#9e9e9e" # Gris
elif porcentaje > -75:
    zona = "Bajista Moderado / Rebote"
    color = "#e57373" # Rojo claro
else:
    zona = "Tendencia Bajista Fuerte (Buscar Ventas)"
    color = "#d50000" # Rojo fuerte

with col2:
    st.markdown("#### Termómetro de Tendencia")
    
    # Métricas
    c1, c2 = st.columns(2)
    c1.metric(label="Puntuación Neta", value=f"{puntuacion_total} / {MAX_PUNTOS}")
    c2.metric(label="Sesgo Global", value=f"{porcentaje:.1f}%")
    
    # Barra de progreso visual con HTML/CSS
    # Ajustamos el porcentaje visual de 0 a 100 para la barra de fondo
    porcentaje_visual = (porcentaje + 100) / 2
    
    st.markdown(f"""
    <div style="width: 100%; background-color: #2b2b2b; border-radius: 5px; height: 30px; margin-top: 10px; margin-bottom: 10px; border: 1px solid #555;">
        <div style="width: {porcentaje_visual}%; background-color: {color}; height: 100%; border-radius: 4px; transition: width 0.5s ease-in-out;"></div>
    </div>
    <div style="text-align: center; padding: 10px; border-radius: 5px; background-color: {color}20; border: 1px solid {color};">
        <h4 style="color: {color}; margin: 0;">{zona}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Botón para limpiar la ficha actual
    if st.button(f"Resetear ficha de {activo_actual}", use_container_width=True):
        st.session_state['evaluaciones'][activo_actual] = {tf: 0 for tf in TEMPORALIDADES.keys()}
        st.rerun()
