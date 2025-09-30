# Optimizador de Rutas VRP

Una aplicación web para optimizar rutas de vehículos usando Taipy y OR-Tools.

## 🚀 Características

- Optimización de rutas con restricciones de capacidad
- Interfaz gráfica intuitiva
- Visualización de rutas con NetworkX
- Matriz de distancias editable

## 📦 Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/esnilg/vrp_ortools.git
cd vrp_ortools
```

2. Crea y activa un nuevo entorno conda (recomendado):
```bash
conda create -n vrp_env python=3.8
conda activate vrp_env
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

4. Ejecuta la aplicación:
```bash
python src/app.py
```

5. Abre tu navegador en http://localhost:10000

🛠️ Tecnologías

- Python 3.8+
- Taipy
- OR-Tools
- Pandas
- Matplotlib
- NetworkX

📝 Uso

- Modifica las demandas de los clientes
- Ajusta la capacidad del vehículo
- Haz clic en "Run Optimization"
- Visualiza la ruta óptima y métricas
