import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import os

# =========================
# 1. Datos iniciales
# =========================
def initialize_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.matrix_data = pd.DataFrame([
            [0, 9, 4, 7, 3],
            [9, 0, 8, 2, 6],
            [4, 8, 0, 3, 7],
            [7, 2, 3, 0, 5],
            [3, 6, 7, 5, 0]
        ], columns=["Depósito", "Cliente1", "Cliente2", "Cliente3", "Cliente4"],
           index=["Depósito", "Cliente1", "Cliente2", "Cliente3", "Cliente4"])
        st.session_state.demands = [0, 10, 15, 5, 8]
        st.session_state.capacity = 40  # Corrected capacity
        st.session_state.optimal_route_str = "No calculada"
        st.session_state.total_distance_str = "N/A"
        st.session_state.capacity_used = 0
        st.session_state.efficiency = "N/A"
        st.session_state.route_img = None
        st.session_state.optimal_route = []

# =========================
# 2. Función de optimización (VRP)
# =========================
def solve_vrp(demands, capacity, matrix):
    demands_int = [int(d) for d in demands]
    matrix_int = [[int(x) for x in row] for row in matrix]
    capacity_int = int(capacity)
    vehicle_capacities = [capacity_int]
    num_vehicles = 1
    depot = 0

    manager = pywrapcp.RoutingIndexManager(len(matrix_int), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        return matrix_int[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        return demands_int[manager.IndexToNode(from_index)]
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, vehicle_capacities, True, "Capacity"
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(5)

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        index = routing.Start(0)
        route, total_distance = [], 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        route.append(manager.IndexToNode(index))
        return route, total_distance
    else:
        return [], 0

# =========================
# 3. Funciones Auxiliares de la App
# =========================
def generate_route_image(route, matrix_data):
    if not route:
        return None
    try:
        G = nx.DiGraph()
        labels = list(matrix_data.columns)
        for i in range(len(labels)):
            G.add_node(i, label=labels[i])
        edges = [(route[i], route[i+1]) for i in range(len(route)-1)]
        G.add_edges_from(edges)
        pos = nx.circular_layout(G)
        plt.figure(figsize=(8, 6))
        node_labels = {i: labels[i] for i in range(len(labels))}
        nx.draw(G, pos, with_labels=True, labels=node_labels,
                node_color="skyblue", node_size=2000, font_size=12,
                font_weight="bold", arrows=True, edge_color="gray",
                width=2, arrowstyle='->', arrowsize=20)
        edge_labels = {}
        for i in range(len(route)-1):
            from_node, to_node = route[i], route[i+1]
            edge_labels[(from_node, to_node)] = matrix_data.iloc[from_node, to_node]
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', font_size=10)
        plt.title("Ruta Óptima", fontsize=16, fontweight='bold')
        img_path = "route_plot.png"
        plt.savefig(img_path, dpi=100, bbox_inches='tight')
        plt.close()
        return img_path
    except Exception as e:
        st.error(f"Error generando imagen: {e}")
        return None

def run_optimization():
    try:
        route, distance = solve_vrp(st.session_state.demands, st.session_state.capacity, st.session_state.matrix_data.values.tolist())

        st.session_state.optimal_route = route
        st.session_state.optimal_route_str = f"{' → '.join(map(str, route))}" if route else "No se encontró solución"
        st.session_state.total_distance_str = f"{distance} unidades" if distance is not None else "N/A"

        if route:
            st.session_state.capacity_used = sum(st.session_state.demands[i] for i in route if i != 0)
            st.session_state.efficiency = f"{(distance/(len(route)-1) if len(route)>1 else 0):.1f} uds/cliente"
        else:
            st.session_state.capacity_used = 0
            st.session_state.efficiency = "N/A"

        st.session_state.route_img = generate_route_image(route, st.session_state.matrix_data)
    except Exception as e:
        st.exception(e)

# =========================
# 4. Streamlit UI
# =========================
st.set_page_config(layout="wide", page_title="Optimizador de Rutas")

initialize_session_state()

st.title("🚚 Optimizador de Rutas de Vehículos (VRP)")

col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.header("📊 Datos de Entrada")

    with st.expander("🗺️ Matriz de Distancias", expanded=True):
        st.session_state.matrix_data = st.data_editor(st.session_state.matrix_data)

    st.subheader("📦 Demandas por Cliente")
    demands_cols = st.columns(len(st.session_state.demands))
    new_demands = st.session_state.demands.copy()
    client_labels = list(st.session_state.matrix_data.columns)

    for i, col in enumerate(demands_cols):
        with col:
            label = client_labels[i]
            new_demands[i] = st.number_input(
                label,
                min_value=0,
                value=new_demands[i],
                step=1,
                key=f"demand_{i}",
                disabled=(i==0)
            )
    st.session_state.demands = new_demands

    st.subheader("🚛 Capacidad del Vehículo")
    st.session_state.capacity = st.number_input("Capacidad", min_value=1, value=st.session_state.capacity, step=1)

    if st.button("🚀 Run Optimization", type="primary", use_container_width=True):
        run_optimization()

with col2:
    st.header("📈 Resultados de la Optimización")

    if st.session_state.optimal_route:
        st.success(f"**Ruta Óptima:** {st.session_state.optimal_route_str}")

        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Distancia Total", st.session_state.total_distance_str)
        with metric_cols[1]:
            st.metric("Capacidad Utilizada", f"{st.session_state.capacity_used} / {st.session_state.capacity}")
        with metric_cols[2]:
            st.metric("Eficiencia", st.session_state.efficiency)

        st.subheader("🗺️ Visualización de la Ruta")
        if st.session_state.route_img and os.path.exists(st.session_state.route_img):
            st.image(st.session_state.route_img, caption="Diagrama de la ruta óptima.")
        else:
            st.warning("No se pudo generar la imagen de la ruta.")

    else:
        st.info("Aún no se ha calculado una ruta. Presiona 'Run Optimization'.")

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton>button {
        font-size: 1.2rem;
        padding: 0.8rem 1.5rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)