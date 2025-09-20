import taipy as tp
from taipy import Gui
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import os

# =========================
# 1. Datos iniciales
# =========================
initial_matrix_data = pd.DataFrame([
    [0, 9, 4, 7, 3],
    [9, 0, 8, 2, 6],
    [4, 8, 0, 3, 7],
    [7, 2, 3, 0, 5],
    [3, 6, 7, 5, 0]
], columns=["Depósito", "Cliente1", "Cliente2", "Cliente3", "Cliente4"])

initial_demands = [0, 10, 15, 5, 8]   # depósito = 0
initial_capacity = 20

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
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

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
# 3. Variables de GUI
# =========================
# Variables adicionales para la interfaz mejorada
optimal_route_str = "No calculada"
total_distance_str = "N/A"
capacity_used = 0
efficiency = "N/A"
route_img = None  # Inicializar como None
demands = initial_demands.copy()
capacity = initial_capacity
optimal_route = []
total_distance = None
matrix_data = initial_matrix_data

# Función para generar el gráfico de la ruta
def generate_route_image(route, state):
    if not route:
        return None
        
    try:
        # Dibujar grafo de la ruta
        G = nx.DiGraph()
        labels = ["Depósito", "Cliente1", "Cliente2", "Cliente3", "Cliente4"]

        # Añadir nodos
        for i in range(len(labels)):
            G.add_node(i, label=labels[i])

        # Añadir arcos según la ruta
        edges = [(route[i], route[i+1]) for i in range(len(route)-1)]
        G.add_edges_from(edges)

        pos = nx.circular_layout(G)  # disposición circular
        
        plt.figure(figsize=(6, 4))
        nx.draw(G, pos, with_labels=True, labels={i: labels[i] for i in range(len(labels))},
                node_color="lightblue", node_size=1500, font_size=10, 
                font_weight="bold", arrows=True, edge_color="gray", 
                width=2, arrowstyle='->', arrowsize=20)
        
        # Añadir pesos de las aristas
        edge_labels = {}
        for i in range(len(route)-1):
            from_node = route[i]
            to_node = route[i+1]
            edge_labels[(from_node, to_node)] = initial_matrix_data.iloc[from_node, to_node]
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red')
        
        plt.title("Ruta Óptima", fontsize=14, fontweight='bold')
        plt.axis('off')  # Ocultar ejes
        #plt.tight_layout()
        
        # Guardar la imagen
        img_path = "route_plot.png"
        #plt.savefig(img_path, dpi=100, bbox_inches='tight')
        plt.savefig(img_path, dpi=100, bbox_inches='tight', pad_inches=0.5)
        plt.close()
        
        return img_path
        
    except Exception as e:
        print(f"Error generando imagen: {e}")
        return None

# Función de optimización
def run_optimization(state):
    # Llamar directamente a la función de optimización
    route, distance = solve_vrp(state.demands, state.capacity, initial_matrix_data.values.tolist())
    
    # Actualizar el estado
    state.optimal_route = route
    state.total_distance = distance
    
    # Actualizar las cadenas para mostrar
    state.optimal_route_str = f"{' → '.join(map(str, route))}" if route else "No se encontró solución"
    state.total_distance_str = f"{distance} unidades" if distance else "N/A"
    
    # Calcular capacidad utilizada
    if route:
        state.capacity_used = sum(state.demands[i] for i in route if i != 0)
        state.efficiency = f"{(distance/(len(route)-1) if len(route)>1 else 0):.1f} uds/cliente"
    else:
        state.capacity_used = 0
        state.efficiency = "N/A"
    
    # Generar y actualizar la imagen de la ruta
    state.route_img = generate_route_image(route, state)

# =========================
# 4. Página GUI
# =========================
page = """
# 🚚 Optimizador de Rutas de Vehículos

<|layout|columns=7 5|gap=30px|

<|part|class_name=card p2|
## 📊 Datos de Entrada

### 🗺️ Matriz de Distancias
<|{matrix_data}|table|editable|width=100%|class_name=fullwidth|>

### 📦 Demandas por Cliente
**Leyenda:** Depósito: 0, Cliente1: 1, Cliente2: 2, Cliente3: 3, Cliente4: 4

<|layout|columns=1 1 1 1 1|gap=10px|
<|part|class_name=demand-card|
**🏢 Depósito**  
<|{demands[0]}|input|type=number|disabled|class_name=demand-input|>
|>

<|part|class_name=demand-card|
**👤 Cliente 1**  
<|{demands[1]}|input|type=number|class_name=demand-input|>
|>

<|part|class_name=demand-card|
**👤 Cliente 2**  
<|{demands[2]}|input|type=number|class_name=demand-input|>
|>

<|part|class_name=demand-card|
**👤 Cliente 3**  
<|{demands[3]}|input|type=number|class_name=demand-input|>
|>

<|part|class_name=demand-card|
**👤 Cliente 4**  
<|{demands[4]}|input|type=number|class_name=demand-input|>
|>
|>

### 🚛 Capacidad del Vehículo
<|{capacity}|input|type=number|class_name=capacity-input|>

<|Run Optimization|button|on_action=run_optimization|class_name=primary|>
|>

<|part|class_name=card p2|
## 📈 Resultados de la Optimización

### 🎯 Solución Encontrada
<|part|class_name=result-section|
**🗺️ Ruta Óptima:**  
<|{optimal_route_str}|text|class_name=route-result|>
|>

<|part|class_name=result-section|
**📏 Distancia Total:**  
<|{total_distance_str}|text|class_name=distance-result|>
|>

<|part|class_name=result-section|
**📊 Métricas:**  
- **Clientes visitados:** <|{len(optimal_route)-2 if optimal_route else 0}|text|>
- **Capacidad utilizada:** <|{capacity_used if optimal_route else 0}|text|> / <|{capacity}|text|>
- **Eficiencia de ruta:** <|{efficiency}|text|>
|>

### 🗺️ Visualización de la Ruta
<|part|class_name=map-container|
<|{route_img}|image|width=100%|>
|>
|>
|>

<style>
.card {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 15px;
    border: 2px solid #dee2e6;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.demand-card {
    background: white;
    padding: 10px;
    border-radius: 10px;
    text-align: center;
    border: 1px solid #ced4da;
}

.demand-input input {
    text-align: center;
    font-weight: bold;
    background: #f8f9fa;
}

.capacity-input input {
    font-weight: bold;
    background: #fff3cd;
}

.primary {
    background: linear-gradient(45deg, #007bff, #0056b3);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: bold;
    margin-top: 20px;
}

.primary:hover {
    background: linear-gradient(45deg, #0056b3, #004494);
}

.result-section {
    background: white;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    border-left: 4px solid #007bff;
}

.route-result {
    font-family: 'Courier New', monospace;
    font-weight: bold;
    color: #28a745;
    font-size: 1.1em;
}

.distance-result {
    font-family: 'Arial', sans-serif;
    font-weight: bold;
    color: #dc3545;
    font-size: 1.2em;
}

.map-container {
    background: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    min-height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.fullwidth table {
    width: 100% !important;
}

.p2 {
    padding: 20px;
}

h2, h3, h4 {
    color: #2c3e50;
}
</style>
"""

# =========================
# 5. Ejecutar GUI
# =========================
if __name__ == "__main__":
    gui = Gui(page)
    gui.run(host="0.0.0.0", port=10000,dark_mode=False)