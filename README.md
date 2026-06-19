# PocketFora: Sistema de Gestión Financiera Automatizada

## Resumen Ejecutivo
**PocketFora** es una aplicación de escritorio diseñada para automatizar el registro, categorización y seguimiento de gastos personales. El sistema está optimizado para estudiantes foráneos y utiliza el procesamiento de códigos QR presentes en las facturas electrónicas colombianas bajo el estándar DIAN.

## Arquitectura de Software
El sistema implementa una **arquitectura de tres capas** para asegurar la mantenibilidad y separación de responsabilidades:

1.  **Capa de Presentación:** Interfaz gráfica desarrollada con **Tkinter** para entornos Windows.
2.  **Capa de Lógica de Negocio:** Módulos especializados en Python:
    * `qr_scanner.py`: Decodificación de códigos QR mediante `pyzbar` y `OpenCV`.
    * `invoice_parser.py`: Motor de *parsing* basado en reglas (Regex) para el procesamiento de datos del formato DIAN.
    * `db_manager.py`: Gestión de operaciones CRUD.
    * `reporter.py`: Generación de análisis financieros y reportes mensuales.
3.  **Capa de Persistencia:** Sistema de gestión de bases de datos relacionales basado en **SQLite** para almacenamiento local.

## Especificaciones Técnicas
* **Lenguaje:** Python.
* **Frameworks de Visión Computacional:** OpenCV, pyzbar.
* **Frameworks de UI:** Tkinter.
* **Base de Datos:** SQLite.

## Rendimiento Operativo
[cite_start]PocketFora ha sido validado mediante pruebas de rendimiento y usabilidad, superando los objetivos de latencia[cite: 19]:

| Operación | Tiempo Medio | Estado |
| :--- | :--- | :--- |
| Decodificación QR | 0.42 s | Superado  |
| Parsing (Texto QR) | 0.07 s | Superado  |
| Flujo Completo (Img -> BD) | 0.92 s | Superado  |

## Metodología de Desarrollo
El ciclo de vida de desarrollo de software (SDLC) se ejecutó bajo un marco de trabajo ágil basado en **Scrum**, estructurado en Sprints iterativos de 3 semanas. Este enfoque permitió una entrega incremental de valor, garantizando la trazabilidad y calidad del sistema desde la fase de arquitectura hasta la implementación final.

### Aseguramiento de la Calidad (QA)
La robustez del sistema fue validada mediante un conjunto de **34 casos de pruebas unitarias**, las cuales abarcaron la integridad de los módulos de escaneo, la precisión del motor de *parsing* y la consistencia de la capa de persistencia. El proceso culminó con una tasa de éxito del 87.56%, cumpliendo con los estándares de calidad definidos para el proyecto.
