import streamlit as st
import pandas as pd
import numpy as np
import re
from urllib.parse import quote
import base64
from pathlib import Path

# ===================================================================
# LÓGICA DO SELETOR (INTOCADA, CONFORME SOLICITADO)
# ===================================================================
# ===================================================================
# CONFIGURAÇÕES GERAIS
# ===================================================================
MOSTRAR_CALCULADORA = False # Mude para True para exibir a aba da calculadora
# -------------------------------------------------------------------
# Funções Auxiliares (Imagens, PDF)
# -------------------------------------------------------------------
if 'mostrar_lista_pecas' not in st.session_state: st.session_state.mostrar_lista_pecas = False
if 'mostrar_desenho' not in st.session_state: st.session_state.mostrar_desenho = False
if 'mostrar_desenho_visualizacao' not in st.session_state: st.session_state.mostrar_desenho_visualizacao = False
if 'mostrar_lista_visualizacao' not in st.session_state: st.session_state.mostrar_lista_visualizacao = False
if 'mostrar_buscador_modelo' not in st.session_state: st.session_state.mostrar_buscador_modelo = False
if 'mostrar_grafico' not in st.session_state: st.session_state.mostrar_grafico = False

# Adicione este bloco para esconder o menu de navegação
st.markdown(
    """
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_data
def image_to_base64(img_path):
    """Converte um arquivo de imagem para string base64."""
    try:
        path = Path(img_path)
        with path.open("rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def mostrar_pdf(caminho_arquivo, legenda="Visualização do Documento"):
    """Exibe a primeira página de um PDF como imagem diretamente no Streamlit."""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        doc = fitz.open(caminho_arquivo)
        page = doc.load_page(0)
        
        zoom = 3.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))
        
        st.image(image, caption=legenda, use_container_width=True)
        
    except FileNotFoundError:
        st.warning(f"Arquivo não encontrado para este modelo.")
    except Exception as e:
        st.error(f"Não foi possível exibir o PDF: {e}")

# -------------------------------------------------------------------
# Dicionário de Traduções
# -------------------------------------------------------------------
TRADUCOES = {
    'pt': {
        'page_title': "Seletor Higra Mining",
        'main_title': "Seletor de Bombas Hidráulicas Higra Mining",
        'welcome_message': "Bem-vindo! Entre com os dados do seu ponto de trabalho para encontrar a melhor solução.",
        'input_header': "Parâmetros de Entrada",
        'eletric_freq_title': "Frequência Elétrica",
        'freq_header': "Frequência",
        'flow_header': "**Vazão Desejada**",
        'graph_header': "📊 Gráfico de Performance",
        'drawing_header': "📐 Desenho Dimensional",
        'selector_tab_label': "Seletor por Ponto de Trabalho",
        'finder_tab_label': "Buscador por Modelo",
        'parts_list_header': "📋 Lista de Peças",
        'view_graph_button': "Visualizar Gráfico",
        'close_graph_button': "Fechar Gráfico",
        'pressure_header': "**Pressão Desejada**",
        'flow_value_label': "Valor da Vazão",
        'pressure_value_label': "Valor da Pressão",
        'view_drawing_button': "Visualizar Desenho",
        'show_finder_button': "🔎 Buscar por Modelo da Bomba",
        'view_parts_list_button': "Visualizar Lista de Peças",
        'close_view_button': "Fechar Visualização",
        'flow_unit_label': "Unidade Vazão",
        'finder_header': "Busque diretamente pelo modelo da bomba",
        'model_select_label': "1. Selecione o Modelo",
        'motor_select_label': "2. Selecione o Motor (CV)",
        'find_pump_button': "Buscar Bomba",
        'download_graph_button': "Baixar Gráfico",
        'pressure_unit_label': "Unidade Pressão",
        'converted_values_info': "Valores convertidos para a busca: **Vazão: {vazao} m³/h** | **Pressão: {pressao} mca**",
        'search_button': "Buscar Melhor Opção",
        'dimensional_drawing_button': "Desenho Dimensional",
        'dimensional_drawing_warning': "Atenção: O Desenho Dimensional é um documento de referência e pode conter variações. Em caso de dúvida ou para confirmação mais detalhada, por favor, entre em contato.",
        'parts_list_button': "Lista de Peças",
        'parts_list_warning': "Atenção: A lista de peças é um documento de referência e pode conter variações. Em caso de dúvida ou para confirmação mais detalhada, por favor, entre em contato.",
        'download_parts_list_button': "Baixar Lista de Peças",
        'parts_list_unavailable': "Lista de peças indisponível. Por favor, entre em contato para receber.",
        'spinner_text': "Calculando as melhores opções para {freq}...",
        'results_header': "Resultados da Busca",
        'solution_unique': "✅ Solução encontrada com **BOMBA ÚNICA**:",
        'solution_parallel': "⚠️ Nenhuma bomba única com bom rendimento. Alternativa: **DUAS BOMBAS EM PARALELO**:",
        'solution_parallel_info': "A vazão e potência abaixo são POR BOMBA. Vazão total = 2x.",
        'solution_series': "⚠️ Nenhuma opção única ou paralela. Alternativa: **DUAS BOMBAS EM SÉRIE**:",
        'solution_series_info': "A pressão abaixo é POR BOMBA. Pressão total = 2x.",
        'no_solution_error': "❌ Nenhuma bomba encontrada. Tente outros valores.",
        'quote_button_start': "Fazer Orçamento",
        'quote_options_header': "Passo 1: Selecione os Opcionais da Bomba",
        'quote_continue_button': "Continuar para o Próximo Passo",
        'quote_contact_header': "Passo 2: Seus Dados de Contato",
        'quote_form_name': "Seu Nome *",
        'pipe_material_cs': "Aço Carbono",
        'pipe_material_ss': "Aço Inox",
        'pipe_material_di': "Ferro Dúctil",
        'pipe_material_ci': "Ferro Fundido",
        'pipe_material_pvc': "PVC",
        'footer_copyright': "© 2025 Higra Mining. Todos os direitos reservados.",
        'footer_more_info': "Para mais informações, visite ",
        'footer_our_website': "nosso site ",
        'search_with_data_button': "Buscar Bombas com Estes Dados",
        'search_done_message': "Busca concluída! Os resultados estão na aba 'Seletor por Ponto de Trabalho'.",
        'pipe_material_hdpe': "HDPE (PEAD)",
        'quote_form_email': "Seu E-mail *",
        'quote_form_message': "Mensagem (opcional)",
        'quote_form_button': "Enviar Pedido de Orçamento",
        'quote_form_warning': "Por favor, preencha seu nome e e-mail.",
        'quote_form_success': "Pedido pronto para ser enviado!",
        'download_drawing_button': "Baixar Desenho Dimensional",
        'performance_note': "Nota: Nossos cálculos avançados para encontrar a bomba ideal podem levar alguns segundos. Agradecemos a sua paciência!",
        'drawing_unavailable': "Desenho dimensional indisponível. Entre em contato para receber.",
        'contact_button': "Contato",
        'show_unique_button': "🔍 Mostrar Bombas Únicas",
        'show_systems_button': "🔄 Mostrar Sistemas Múltiplos",
        'view_mode_unique': "Modo de visualização: Bombas Únicas",
        'view_mode_systems': "Modo de visualização: Sistemas Múltiplos",
        'no_unique_pumps': "❌ Nenhuma bomba única encontrada para estes parâmetros.",
        'no_systems_found': "❌ Nenhum sistema com múltiplas bombas encontrado para estes parâmetros.",
        'system_type_single': "Única",
        'system_type_parallel': "{} em Paralelo",
        'system_type_series': "2 em Série",
        'system_type_combined': "{} Bombas ({}x2)",
        'system_type_header': "Tipo de Sistema",
        'pressure_error_header': "Erro de Pressão",
        'relative_error_header': "Erro Relativo",
        'calculator_tab_label': "Calculadora de Sistema",
        'calculator_header': "Calculadora de Ponto de Trabalho",
        'calculator_intro': "Preencha os dados do seu sistema hidráulico para calcular a vazão e a pressão (altura manométrica) necessárias para o seu projeto.",
        'section_general_data': "Dados Gerais do Projeto",
        'desired_flow_rate': "Vazão Requerida",
        'fluid_temperature': "Temperatura do Fluido (°C)",
        'section_piping': "Detalhes da Tubulação",
        'pipe_material': "Material da Tubulação",
        'pipe_diameter': "Diâmetro Interno (mm)",
        'pipe_length': "Comprimento Reto Total (m)",
        'section_elevation': "Elevação (Desnível Geométrico)",
        'suction_elevation': "Altura de Sucção (m)",
        'discharge_elevation': "Altura de Recalque (m)",
        'elevation_help': "Sucção: distância vertical do nível da água até o eixo da bomba. Recalque: distância vertical do eixo da bomba até o ponto de entrega final.",
        'section_fittings': "Acessórios e Perdas Localizadas",
        'elbow_90': "Cotovelo 90°",
        'elbow_45': "Cotovelo 45°",
        'gate_valve': "Válvula Gaveta (Aberta)",
        'check_valve': "Válvula de Retenção",
        'entry_loss': "Perda de Carga na Entrada (Sucção)",
        'exit_loss': "Perda de Carga na Saída (Recalque)",
        'calculate_button': "Calcular Ponto de Trabalho",
        'results_header_calculator': "Resultado do Cálculo",
        'calculated_head': "Altura Manométrica Total Calculada",
        'use_data_button': "Usar estes dados para Buscar a Bomba",
        'no_solution_found': "❌ Nenhuma bomba ou sistema de bombas foi encontrado para este ponto de trabalho. Tente outros valores ou entre em contato com nosso suporte.",
        'quote_form_click_here': "Clique aqui para abrir e enviar o e-mail",
        'quote_form_info': "Seu programa de e-mail padrão será aberto com todas as informações preenchidas.",
        'email_subject': "Pedido de Orçamento via Seletor de Bombas - {nome}",
        'email_body': """Olá,\n\nUm novo pedido de orçamento foi gerado através do Seletor de Bombas.\n\nDADOS DO CLIENTE:\n- Nome: {nome}\n- E-mail: {email}\n\nMENSAGEM:\n{mensagem}\n\n---------------------------------\nPARÂMETROS DA BUSCA:\n- Frequência: {freq}\n- Vazão: {vazao} m³/h\n- Pressão: {pressao} mca\n\n---------------------------------\nRESULTADOS ENCONTRADOS:\n{tabela_resultados}"""
    },
    'en': {
        'page_title': "Higra Mining Selector",
        'main_title': "Higra Mining Hydraulic Pump Selector",
        'welcome_message': "Welcome! Enter your duty point data to find the best solution.",
        'input_header': "Input Parameters",
        'eletric_freq_title': "Electrical Frequency",
        'freq_header': "Frequency",
        'flow_header': "**Desired Flow**",
        'pressure_header': "**Desired Head**",
        'flow_value_label': "Flow Value",
        'finder_header': "Search directly by pump model",
        'model_select_label': "1. Select Model",
        'motor_select_label': "2. Select Motor (CV)",
        'find_pump_button': "Find Pump",
        'pressure_value_label': "Head Value",
        'selector_tab_label': "Selector by Duty Point",
        'finder_tab_label': "Search by Model",
        'flow_unit_label': "Flow Unit",
        'graph_header': "📊 Performance Chart",
        'drawing_header': "📐 Dimensional Drawing",
        'parts_list_header': "📋 Parts List",
        'view_graph_button': "View Chart",
        'show_finder_button': "🔎 Search by Pump Model",
        'close_graph_button': "Close Chart",
        'pressure_unit_label': "Head Unit",
        'view_drawing_button': "View Drawing",
        'view_parts_list_button': "View Parts List",
        'close_view_button': "Close View",
        'parts_list_button': "Parts List",
        'calculator_tab_label': "System Calculator",
        'calculator_header': "Duty Point Calculator",
        'calculator_intro': "Fill in your hydraulic system data to calculate the required flow rate and pressure (total dynamic head) for your project.",
        'section_general_data': "General Project Data",
        'desired_flow_rate': "Required Flow Rate",
        'fluid_temperature': "Fluid Temperature (°C)",
        'section_piping': "Piping Details",
        'pipe_material': "Pipe Material",
        'pipe_material_cs': "Carbon Steel",
        'pipe_material_ss': "Stainless Steel",
        'pipe_material_di': "Ductile Iron",
        'pipe_material_ci': "Cast Iron",
        'pipe_material_pvc': "PVC",
        'download_graph_button': "Download Chart",
        'footer_copyright': "© 2025 Higra Mining. All rights reserved.",
        'footer_more_info': "For more information, visit ",
        'footer_our_website': "our website",
        'search_with_data_button': "Find Pumps with This Data",
        'search_done_message': "Search complete! The results are on the 'Selector by Duty Point' tab.",
        'pipe_material_hdpe': "HDPE",
        'pipe_diameter': "Internal Diameter (mm)",
        'pipe_length': "Total Straight Length (m)",
        'section_elevation': "Elevation (Geometric Head)",
        'suction_elevation': "Suction Head (m)",
        'discharge_elevation': "Discharge Head (m)",
        'elevation_help': "Suction: vertical distance from water level to pump centerline. Discharge: vertical distance from pump centerline to final delivery point.",
        'section_fittings': "Fittings and Minor Losses",
        'elbow_90': "90° Elbow",
        'elbow_45': "45° Elbow",
        'gate_valve': "Gate Valve (Open)",
        'check_valve': "Check Valve",
        'entry_loss': "Entrance Loss (Suction)",
        'exit_loss': "Exit Loss (Discharge)",
        'calculate_button': "Calculate Duty Point",
        'results_header_calculator': "Calculation Result",
        'calculated_head': "Calculated Total Dynamic Head",
        'use_data_button': "Use this Data to Find a Pump",
        'parts_list_warning': "Attention: The parts list is a reference document and may contain variations. If in doubt or for more detailed confirmation, please contact us.",
        'download_parts_list_button': "Download Parts List",
        'parts_list_unavailable': "Parts list unavailable. Please contact us to receive it.",
        'converted_values_info': "Converted values for search: **Flow: {vazao} m³/h** | **Head: {pressao} mca**",
        'search_button': "Find Best Option",
        'spinner_text': "Calculating the best options for {freq}...",
        'results_header': "Search Results",
        'dimensional_drawing_button': "Dimensional Drawing",
        'dimensional_drawing_warning': "Attention: The Dimensional Drawing is a reference document and may contain variations. If in doubt or for more detailed confirmation, please contact us.",
        'solution_unique': "✅ Solution found with a **SINGLE PUMP**:",
        'solution_parallel': "⚠️ No single pump with good efficiency. Alternative: **TWO PUMPS IN PARALLEL**:",
        'solution_parallel_info': "Flow and power below are PER PUMP. Total flow = 2x.",
        'solution_series': "⚠️ No single or parallel option. Alternative: **TWO PUMPS IN SERIES**:",
        'solution_series_info': "Head below is PER PUMP. Total head = 2x.",
        'no_solution_error': "❌ No pump found. Try other values.",
        'quote_button_start': "Request a Quote",
        'quote_options_header': "Step 1: Select Pump Options",
        'quote_continue_button': "Continue to Next Step",
        'quote_contact_header': "Step 2: Your Contact Information",
        'quote_form_name': "Your Name *",
        'download_drawing_button': "Download Dimensional Drawing",
        'drawing_unavailable': "Dimensional drawing unavailable. Please contact us to receive it.",
        'contact_button': "Contact",
        'pressure_error_header': "Pressure Error",
        'relative_error_header': "Relative Error",
        'system_type_header': "System Type",
        'no_solution_found': "❌ No pump or pump system was found for this duty point. Try other values or contact our support.",
        'performance_note': "Note: Our advanced calculations to find the ideal pump may take a few seconds. We appreciate your patience!",
        'quote_form_email': "Your Email *",
        'system_type_single': "Single",
        'show_unique_button': "🔍 Show Single Pumps",
        'show_systems_button': "🔄 Show Multiple Systems",
        'view_mode_unique': "Viewing mode: Single Pumps",
        'view_mode_systems': "Viewing mode: Multiple Systems",
        'no_unique_pumps': "❌ No single pump found for these parameters.",
        'no_systems_found': "❌ No multiple pump system found for these parameters.",
        'system_type_parallel': "{} in Parallel",
        'system_type_series': "2 in Series",
        'system_type_combined': "{} Pumps ({}x2)",
        'quote_form_message': "Message (optional)",
        'quote_form_button': "Send Quote Request",
        'quote_form_warning': "Please fill in your name and email.",
        'quote_form_success': "Request ready to be sent!",
        'quote_form_click_here': "Click here to open and send the email",
        'quote_form_info': "Your default email client will open with all the information pre-filled.",
        'email_subject': "Quote Request via Pump Selector - {nome}",
        'email_body': """Hello,\n\nA new quote request has been generated through the Pump Selector.\n\nCUSTOMER DATA:\n- Name: {nome}\n- Email: {email}\n\nMESSAGE:\n{mensagem}\n\n---------------------------------\nSEARCH PARAMETERS:\n- Frequency: {freq}\n- Flow: {vazao} m³/h\n- Head: {pressao} mca\n\n---------------------------------\nRESULTS FOUND:\n{tabela_resultados}"""
    },
    'es': {
        'page_title': "Selector Higra Mining",
        'main_title': "Selector de Bombas Hidráulicas Higra Mining",
        'welcome_message': "¡Bienvenido! Ingrese los datos de su punto de trabajo para encontrar la mejor solución.",
        'input_header': "Parámetros de Entrada",
        'eletric_freq_title': "Frecuencia Eléctrica",
        'freq_header': "Frecuencia",
        'flow_header': "**Caudal Deseado**",
        'pressure_header': "**Altura Deseada**",
        'show_finder_button': "🔎 Buscar por Modelo de Bomba",
        'flow_value_label': "Valor del Caudal",
        'graph_header': "📊 Gráfico de Rendimiento",
        'drawing_header': "📐 Dibujo Dimensional",
        'selector_tab_label': "Selector por Punto de Trabajo",
        'finder_tab_label': "Buscador por Modelo",
        'parts_list_header': "📋 Lista de Repuestos",
        'view_graph_button': "Visualizar Gráfico",
        'close_graph_button': "Cerrar Gráfico",
        'view_drawing_button': "Visualizar Dibujo",
        'view_parts_list_button': "Visualizar Lista de Repuestos",
        'close_view_button': "Cerrar Visualización",
        'pressure_value_label': "Valor de la Altura",
        'finder_header': "Busque directamente por el modelo de la bomba",
        'model_select_label': "1. Seleccione el Modelo",
        'motor_select_label': "2. Seleccione el Motor (CV)",
        'find_pump_button': "Buscar Bomba",
        'download_graph_button': "Descargar Gráfico",
        'search_with_data_button': "Buscar Bombas con Estos Datos",
        'search_done_message': "¡Búsqueda completa! Los resultados están en la pestaña 'Selector por Punto de Trabajo'.",
        'calculator_tab_label': "Calculadora de Sistema",
        'calculator_header': "Calculadora de Punto de Trabajo",
        'calculator_intro': "Complete los datos de su sistema hidráulico para calcular el caudal y la presión (altura manométrica total) necesarios para su proyecto.",
        'section_general_data': "Datos Generales del Proyecto",
        'desired_flow_rate': "Caudal Requerido",
        'fluid_temperature': "Temperatura del Fluido (°C)",
        'section_piping': "Detalles de la Tubería",
        'pipe_material': "Material de la Tubería",
        'pipe_diameter': "Diámetro Interno (mm)",
        'pipe_length': "Longitud Recta Total (m)",
        'section_elevation': "Elevación (Altura Geométrica)",
        'suction_elevation': "Altura de Succión (m)",
        'discharge_elevation': "Altura de Descarga (m)",
        'elevation_help': "Succión: distancia vertical desde el nivel del agua hasta el eje de la bomba. Descarga: distancia vertical desde el eje de la bomba hasta el punto de entrega final.",
        'section_fittings': "Accesorios y Pérdidas Menores",
        'elbow_90': "Codo 90°",
        'elbow_45': "Codo 45°",
        'footer_copyright': "© 2025 Higra Mining. Todos los derechos reservados.",
        'footer_more_info': "Para más información, visite ",
        'footer_our_website': "nuestro sitio web",
        'pipe_material_cs': "Acero al Carbono",
        'pipe_material_ss': "Acero Inoxidable",
        'pipe_material_di': "Hierro Dúctil",
        'pipe_material_ci': "Hierro Fundido",
        'pipe_material_pvc': "PVC",
        'pipe_material_hdpe': "HDPE (PEAD)",
        'gate_valve': "Válvula de Compuerta (Abierta)",
        'check_valve': "Válvula de Retención",
        'entry_loss': "Pérdida de Entrada (Succión)",
        'exit_loss': "Pérdida de Salida (Descarga)",
        'calculate_button': "Calcular Punto de Trabajo",
        'results_header_calculator': "Resultado del Cálculo",
        'calculated_head': "Altura Manométrica Total Calculada",
        'use_data_button': "Usar estos datos para Buscar la Bomba",
        'flow_unit_label': "Unidad Caudal",
        'parts_list_button': "Lista de Repuestos",
        'parts_list_warning': "Atención: La lista de repuestos es un documento de referencia y puede contener variaciones. En caso de duda o para una confirmación más detallada, póngase en contacto.",
        'download_parts_list_button': "Descargar Lista de Repuestos",
        'parts_list_unavailable': "Lista de repuestos no disponible. Por favor, póngase en contacto para recibirla.",
        'pressure_unit_label': "Unidad Altura",
        'converted_values_info': "Valores convertidos para la búsqueda: **Caudal: {vazao} m³/h** | **Altura: {pressao} mca**",
        'search_button': "Buscar Mejor Opción",
        'dimensional_drawing_button': "Dibujo Dimensional",
        'dimensional_drawing_warning': "Atención: El Dibujo Dimensional es un documento de referencia y puede contener variaciones. En caso de duda o para una confirmación más detallada, por favor, póngase en contacto.",
        'spinner_text': "Calculando las mejores opciones para {freq}...",
        'results_header': "Resultados de la Búsqueda",
        'solution_unique': "✅ Solución encontrada con **BOMBA ÚNICA**:",
        'solution_parallel': "⚠️ Ninguna bomba única con buen rendimiento. Alternativa: **DOS BOMBAS EN PARALELO**:",
        'solution_parallel_info': "El caudal y la potencia a continuación son POR BOMBA. Caudal total = 2x.",
        'solution_series': "⚠️ Ninguna opción única o en paralelo. Alternativa: **DOS BOMBAS EN SERIE**:",
        'solution_series_info': "La altura a continuación es POR BOMBA. Altura total = 2x.",
        'no_solution_error': "❌ No se encontró ninguna bomba. Pruebe con otros valores.",
        'quote_button_start': "Solicitar Cotización",
        'quote_options_header': "Paso 1: Seleccione Opcionales de la Bomba",
        'quote_continue_button': "Continuar al Siguiente Paso",
        'quote_contact_header': "Paso 2: Sus Datos de Contacto",
        'quote_form_name': "Su Nombre *",
        'quote_form_email': "Su Correo Electrónico *",
        'quote_form_message': "Mensaje (opcional)",
        'download_drawing_button': "Descargar Dibujo Dimensional",
        'drawing_unavailable': "Dibujo dimensional no disponible. Contáctenos para recibirlo.",
        'contact_button': "Contacto",
        'system_type_single': "Única",
        'show_unique_button': "🔍 Mostrar Bombas Únicas",
        'show_systems_button': "🔄 Mostrar Sistemas Múltiples",
        'view_mode_unique': "Modo de visualización: Bombas Únicas",
        'view_mode_systems': "Modo de visualización: Sistemas Múltiples",
        'no_unique_pumps': "❌ No se encontraron bombas únicas para estos parámetros.",
        'no_systems_found': "❌ No se encontraron sistemas de bombas múltiples para estos parámetros.",
        'pressure_error_header': "Error de Presión",
        'relative_error_header': "Error Relativo",
        'system_type_parallel': "{} en Paralelo",
        'system_type_series': "2 en Serie",
        'system_type_combined': "{} Bombas ({}x2)",
        'system_type_header': "Tipo de Sistema",
        'no_solution_found': "❌ No se encontró ninguna bomba o sistema de bombas para este punto de trabajo. Intente otros valores o póngase en contacto con nuestro soporte.",
        'performance_note': "Nota: Nuestros cálculos avanzados para encontrar la bomba ideal pueden tardar unos segundos. ¡Agradecemos su paciencia!",
        'quote_form_button': "Enviar Solicitud de Cotización",
        'quote_form_warning': "Por favor, complete su nombre y correo electrónico.",
        'quote_form_success': "¡Solicitud lista para ser enviada!",
        'quote_form_click_here': "Haga clic aquí para abrir y enviar el correo",
        'quote_form_info': "Su cliente de correo electrónico predeterminado se abrirá con toda la información completada.",
        'email_subject': "Solicitud de Cotización vía Selector de Bombas - {nome}",
        'email_body': """Hola,\n\nSe ha generado una nueva solicitud de cotización a través del Selector de Bombas.\n\nDATOS DEL CLIENTE:\n- Nombre: {nome}\n- Correo Electrónico: {email}\n\nMENSAJE:\n{mensagem}\n\n---------------------------------\nPARÁMETROS DE BÚSQUEDA:\n- Frecuencia: {freq}\n- Caudal: {vazao} m³/h\n- Altura: {pressao} mca\n\n---------------------------------\nRESULTADOS ENCONTRADOS:\n{tabela_resultados}"""
    }
}

# ===================================================================
# LÓGICA DA CALCULADORA DE PONTO DE TRABALHO
# ===================================================================
import math

# --- DADOS DE ENGENHARIA ---
# Rugosidade Absoluta (ε) em metros para diferentes materiais
RUGOSIDADE_MATERIAL = {
    'cs': 0.000046,   # Aço Carbono
    'ss': 0.000002,   # Aço Inox
    'di': 0.00024,    # Ferro Dúctil
    'ci': 0.00026,    # Ferro Fundido
    'pvc': 0.0000015, # PVC
    'hdpe': 0.0000015 # HDPE (PEAD)
}

# Coeficientes de Perda Localizada (K) para acessórios comuns
COEFICIENTE_K_ACESSORIOS = {
    'cotovelo_90': 0.9,
    'cotovelo_45': 0.4,
    'valvula_gaveta': 0.2,
    'valvula_retencao': 2.5
}

# Propriedades da Água (Viscosidade Cinemática ν em m²/s) por Temperatura (°C)
# Tabela simplificada para interpolação linear
VISCOSIDADE_AGUA = {
    0: 1.787e-6,
    10: 1.307e-6,
    20: 1.004e-6,
    30: 0.801e-6,
    40: 0.658e-6,
    50: 0.553e-6,
    60: 0.474e-6,
    70: 0.413e-6,
    80: 0.365e-6,
    90: 0.326e-6,
    100: 0.294e-6
}

def obter_viscosidade(temp_c):
    """Calcula a viscosidade cinemática da água por interpolação linear."""
    temps = sorted(VISCOSIDADE_AGUA.keys())
    if temp_c <= temps[0]: return VISCOSIDADE_AGUA[temps[0]]
    if temp_c >= temps[-1]: return VISCOSIDADE_AGUA[temps[-1]]
    
    for i, t_upper in enumerate(temps):
        if temp_c < t_upper:
            t_lower = temps[i-1]
            v_lower = VISCOSIDADE_AGUA[t_lower]
            v_upper = VISCOSIDADE_AGUA[t_upper]
            # Interpolação
            return v_lower + (v_upper - v_lower) * (temp_c - t_lower) / (t_upper - t_lower)

def calcular_ponto_trabalho(dados):
    """
    Função principal que calcula a Altura Manométrica Total (AMT).
    Todos os dados de entrada já devem estar no Sistema Internacional (m, m³/s, etc.).
    """
    g = 9.81 # Aceleração da gravidade (m/s²)
    
    # 1. Propriedades do Sistema e Fluido
    vazao_m3s = dados['vazao_m3h'] / 3600
    diametro_m = dados['diametro_mm'] / 1000
    comprimento_m = dados['comprimento_m']
    rugosidade_m = RUGOSIDADE_MATERIAL[dados['material_key']]
    viscosidade_m2s = obter_viscosidade(dados['temperatura_c'])

    # 2. Cálculos Hidráulicos Básicos
    area_m2 = math.pi * (diametro_m ** 2) / 4
    velocidade_ms = vazao_m3s / area_m2
    reynolds = (velocidade_ms * diametro_m) / viscosidade_m2s

    # 3. Fator de Atrito (f) - Usando a fórmula de Swamee-Jain (precisa e não-iterativa)
    # Válida para 5000 < Re < 10^8 e 10^-6 < ε/D < 10^-2
    rugosidade_relativa = rugosidade_m / diametro_m
    fator_atrito = 0.25 / (math.log10((rugosidade_relativa / 3.7) + (5.74 / (reynolds ** 0.9))))**2

    # 4. Cálculo das Perdas de Carga
    # a) Perda de Carga Contínua (Darcy-Weisbach)
    perda_continua_m = fator_atrito * (comprimento_m / diametro_m) * (velocidade_ms ** 2) / (2 * g)

    # b) Perda de Carga Localizada
    k_total = (
        dados['qtd_cotovelo90'] * COEFICIENTE_K_ACESSORIOS['cotovelo_90'] +
        dados['qtd_cotovelo45'] * COEFICIENTE_K_ACESSORIOS['cotovelo_45'] +
        dados['qtd_valv_gaveta'] * COEFICIENTE_K_ACESSORIOS['valvula_gaveta'] +
        dados['qtd_valv_retencao'] * COEFICIENTE_K_ACESSORIOS['valvula_retencao']
    )
    perda_localizada_m = k_total * (velocidade_ms ** 2) / (2 * g)

    # 5. Altura Geométrica
    altura_geometrica_m = dados['alt_recalque_m'] + dados['alt_succao_m']

    # 6. Altura Manométrica Total (AMT)
    amt_mca = altura_geometrica_m + perda_continua_m + perda_localizada_m
    
    return amt_mca, vazao_m3s * 3600 # Retorna AMT em mca e vazão em m³/h

# -------------------------------------------------------------------
# Funções de Lógica e Processamento de Dados
# -------------------------------------------------------------------
MOTORES_PADRAO = np.array([
    15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 175, 200, 250, 300,
    350, 400, 450, 500, 550, 600
])

def encontrar_motor_final(potencia_real):
    if pd.isna(potencia_real): return np.nan
    candidatos = MOTORES_PADRAO[MOTORES_PADRAO >= potencia_real]
    return candidatos.min() if len(candidatos) > 0 else np.nan

@st.cache_data
def carregar_e_processar_dados(caminho_arquivo):
    try:
        df = pd.read_excel(caminho_arquivo)
        df.columns = df.columns.str.strip().str.upper()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho_arquivo}' não encontrado.")
        return None
    except Exception as e:
        print(f"Ocorreu um erro ao ler o Excel: {e}")
        return None
        
    df["MOTOR PADRÃO (CV)"] = df["POTÊNCIA (HP)"].apply(encontrar_motor_final)
    def extrair_rotor_num(rotor_str):
        match = re.match(r"(\d+)(?:\s*\((\d+)°\))?", str(rotor_str))
        if match:
            base = int(match.group(1)); grau = int(match.group(2)) if match.group(2) else 0
            return base + grau / 100
        return np.nan
    df["ROTORNUM"] = df["ROTOR"].apply(extrair_rotor_num)
    df["ROTOR_MIN_MODELO"] = df.groupby("MODELO")["ROTORNUM"].transform("min")
    df["ROTOR_MAX_MODELO"] = df.groupby("MODELO")["ROTORNUM"].transform("max")
    df["PRESSAO_MAX_MODELO"] = df.groupby("MODELO")["PRESSÃO (MCA)"].transform("max")
    df['POTENCIA_MAX_FAMILIA'] = df.groupby('MODELO')['POTÊNCIA (HP)'].transform('max')
    intervalos_vazao = df.groupby(["MODELO", "ROTOR"])["VAZÃO (M³/H)"].agg(["min", "max"]).reset_index()
    df = pd.merge(df, intervalos_vazao, on=["MODELO", "ROTOR"], how="left", suffixes=("", "_range"))
    df["VAZAO_CENTRO"] = (df["min"] + df["max"]) / 2
    df["ERRO_RELATIVO"] = ((df["VAZÃO (M³/H)"] - df["VAZAO_CENTRO"]) / (df["max"] - df["min"] + 1e-9)) * 100
    df["ABS_ERRO_RELATIVO"] = df["ERRO_RELATIVO"].abs()
    
    return df

def buscar_por_modelo_e_motor(df, modelo, motor):
    if df is None or df.empty:
        return pd.DataFrame()
    df_filtrado = df[
        (df['MODELO'] == modelo) &
        (df['MOTOR PADRÃO (CV)'] == motor)
    ]
    
    if df_filtrado.empty:
        return pd.DataFrame()
        
    melhor_opcao = df_filtrado.loc[df_filtrado['RENDIMENTO (%)'].idxmax()]
    
    resultado_df = pd.DataFrame([melhor_opcao])
    
    resultado_df["TIPO_SISTEMA_CODE"] = "single"
    resultado_df["N_TOTAL_BOMBAS"] = 1
    
    colunas_finais = [
       'MODELO', 'ROTOR', 'VAZÃO (M³/H)', 'PRESSÃO (MCA)', 'ERRO_PRESSAO', 'ERRO_RELATIVO',
       'RENDIMENTO (%)', 'POTÊNCIA (HP)', 'MOTOR FINAL (CV)', 
       'TIPO_SISTEMA_CODE', 'N_TOTAL_BOMBAS',
       'ERRO_PRESSAO_ABS', 'ABS_ERRO_RELATIVO' 
    ]
    
    resultado_df = resultado_df.rename(columns={'MOTOR PADRÃO (CV)': 'MOTOR FINAL (CV)'})
    if 'ROTOR' in resultado_df.columns:
        resultado_df = resultado_df.drop(columns=['ROTOR'])
    resultado_df = resultado_df.rename(columns={'ROTORNUM': 'ROTOR'})
    
    colunas_presentes = [col for col in colunas_finais if col in resultado_df.columns]
    
    return resultado_df[colunas_presentes]

def filtrar_e_classificar(df, vazao, pressao, top_n=5, limite_desempate_rendimento=3):
    if df is None or df.empty: 
        return pd.DataFrame()

    mask_vazao = df["VAZÃO (M³/H)"] == vazao
    if not mask_vazao.any():
        return pd.DataFrame()
    df_vazao = df.loc[mask_vazao].copy()
    
    min_max = df_vazao.groupby('MODELO')['PRESSÃO (MCA)'].agg(['min', 'max']).reset_index()
    min_max.columns = ['MODELO', 'PRESSAO_DO_ROTOR_MIN', 'PRESSAO_DO_ROTOR_MAX']
    
    df_vazao = df_vazao.merge(min_max, on='MODELO', how='left')
    
    limite_inferior = df_vazao['PRESSAO_DO_ROTOR_MIN'] * 0.99
    limite_superior = df_vazao['PRESSAO_DO_ROTOR_MAX'] * 1.01
    
    mask_limites = (pressao >= limite_inferior) & (pressao <= limite_superior)
    df_filtrado = df_vazao.loc[mask_limites].copy()
    
    if df_filtrado.empty:
        return pd.DataFrame()

    df_filtrado["ERRO_PRESSAO"] = df_filtrado["PRESSÃO (MCA)"] - pressao
    df_filtrado["MOTOR FINAL (CV)"] = df_filtrado["POTÊNCIA (HP)"].apply(encontrar_motor_final)
    df_filtrado["ERRO_PRESSAO_ABS"] = df_filtrado["ERRO_PRESSAO"].abs()
    
    if df_filtrado.empty: return pd.DataFrame()
    
    df_grupo_controle = df_filtrado.loc[df_filtrado.groupby('MODELO')['ERRO_PRESSAO_ABS'].idxmin()].copy()
    if df_grupo_controle.empty: return pd.DataFrame()

    min_erro_rel = df_grupo_controle["ABS_ERRO_RELATIVO"].min()
    df_grupo_controle["DIF_ERRO_REL"] = df_grupo_controle["ABS_ERRO_RELATIVO"] - min_erro_rel
    
    grupo_A = df_grupo_controle[df_grupo_controle["DIF_ERRO_REL"] <= 10].copy()
    grupo_B = df_grupo_controle[df_grupo_controle["DIF_ERRO_REL"] > 10].copy()
    
    grupo_A = grupo_A.sort_values(by="RENDIMENTO (%)", ascending=False)
    
    if not grupo_A.empty:
        max_rend = grupo_A["RENDIMENTO (%)"].max()
        grupo_A["DIF_REND"] = max_rend - grupo_A["RENDIMENTO (%)"]
        
        subgrupo_A1 = grupo_A[grupo_A["DIF_REND"] <= limite_desempate_rendimento].copy()
        subgrupo_A2 = grupo_A[grupo_A["DIF_REND"] > limite_desempate_rendimento].copy()
        
        subgrupo_A1 = subgrupo_A1.sort_values(by="ERRO_PRESSAO_ABS", ascending=True)
        
        grupo_A = pd.concat([subgrupo_A1, subgrupo_A2])
    
    grupo_B = grupo_B.sort_values(by="ABS_ERRO_RELATIVO", ascending=True)
    
    df_resultado = pd.concat([grupo_A, grupo_B])
    df_resultado = df_resultado.head(top_n)
    df_resultado = df_resultado.drop(columns=["DIF_ERRO_REL", "DIF_REND"], errors="ignore")
    
    colunas_finais = [
        'MODELO', 'ROTOR', 'VAZÃO (M³/H)', 'PRESSÃO (MCA)', 'ERRO_PRESSAO', 'ERRO_RELATIVO',
        'RENDIMENTO (%)', 'POTÊNCIA (HP)', 'MOTOR FINAL (CV)', 'ERRO_PRESSAO_ABS', 'ABS_ERRO_RELATIVO'
    ]   
    if 'ROTOR' in df_resultado.columns:
        df_resultado = df_resultado.drop(columns=['ROTOR'])
        
    df_resultado = df_resultado.rename(columns={'ROTORNUM': 'ROTOR'})
    
    colunas_presentes = [col for col in colunas_finais if col in df_resultado.columns]
    
    return df_resultado[colunas_presentes]

def selecionar_bombas(df, vazao_desejada, pressao_desejada):
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    top_n_unicas = 3
    top_n_multiplas = 5
    
    todas_opcoes = []
    
    resultado_unico = filtrar_e_classificar(df, vazao_desejada, pressao_desejada, top_n=10)
    if not resultado_unico.empty:
        resultado_unico["TIPO_SISTEMA_CODE"] = "single"
        resultado_unico["N_TOTAL_BOMBAS"] = 1
        resultado_unico["PRIORIDADE_TIPO"] = 1
        todas_opcoes.append(resultado_unico)
    
    sistemas_multiplos = []
    
    for num_paralelo in range(2, 16):
        vazao_paralelo = vazao_desejada / num_paralelo
        resultado_paralelo = filtrar_e_classificar(df, vazao_paralelo, pressao_desejada, top_n=top_n_multiplas)
        if not resultado_paralelo.empty:
            resultado_paralelo["TIPO_SISTEMA_CODE"] = "parallel"
            resultado_paralelo["N_TOTAL_BOMBAS"] = num_paralelo
            resultado_paralelo["PRIORIDADE_TIPO"] = 2
            sistemas_multiplos.append(resultado_paralelo)
    
    pressao_serie = pressao_desejada / 2
    resultado_serie = filtrar_e_classificar(df, vazao_desejada, pressao_serie, top_n=top_n_multiplas)
    if not resultado_serie.empty:
        resultado_serie["TIPO_SISTEMA_CODE"] = "series"
        resultado_serie["N_TOTAL_BOMBAS"] = 2
        resultado_serie["PRIORIDADE_TIPO"] = 3
        sistemas_multiplos.append(resultado_serie)
    
    for num_conjuntos in range(2, 6):
        vazao_misto = vazao_desejada / num_conjuntos
        pressao_misto = pressao_desejada / 2
        resultado_misto = filtrar_e_classificar(df, vazao_misto, pressao_misto, top_n=top_n_multiplas)
        if not resultado_misto.empty:
            total_bombas = num_conjuntos * 2
            resultado_misto["TIPO_SISTEMA_CODE"] = "combined"
            resultado_misto["N_TOTAL_BOMBAS"] = total_bombas
            resultado_misto["N_PARALELO"] = num_conjuntos
            resultado_misto["PRIORIDADE_TIPO"] = 4
            sistemas_multiplos.append(resultado_misto)
    
    if todas_opcoes:
        df_unicas = pd.concat(todas_opcoes, ignore_index=True)
    else:
        df_unicas = pd.DataFrame()
        
    if sistemas_multiplos:
        df_multiplas = pd.concat(sistemas_multiplos, ignore_index=True)
        df_multiplas = df_multiplas.sort_values(
            by=["MODELO", "N_TOTAL_BOMBAS", "RENDIMENTO (%)"], 
            ascending=[True, True, False]
        ).drop_duplicates(subset=["MODELO"], keep="first")
    else:
        df_multiplas = pd.DataFrame()
    
    resultados_unicas_finais = []
    if not df_unicas.empty:
        candidatas_unicas = df_unicas.copy()
        
        for _ in range(top_n_unicas):
            if candidatas_unicas.empty:
                break
            
            candidatas_unicas = candidatas_unicas.sort_values(
                by=["RENDIMENTO (%)", "ERRO_PRESSAO_ABS", "ABS_ERRO_RELATIVO"],
                ascending=[False, True, True]
            )
            
            melhor_unica = candidatas_unicas.head(1)
            resultados_unicas_finais.append(melhor_unica)
            
            modelo_remover = melhor_unica["MODELO"].iloc[0]
            candidatas_unicas = candidatas_unicas[candidatas_unicas["MODELO"] != modelo_remover]
    
    resultados_multiplos_finais = []
    if not df_multiplas.empty:
        candidatas_multiplas = df_multiplas.copy()
        
        for _ in range(top_n_multiplas):
            if candidatas_multiplas.empty:
                break
            
            candidatas_multiplas = candidatas_multiplas.sort_values(
                by=["N_TOTAL_BOMBAS", "PRIORIDADE_TIPO", "RENDIMENTO (%)", "ERRO_PRESSAO_ABS", "ABS_ERRO_RELATIVO"],
                ascending=[True, True, False, True, True]
            )
            
            melhor_multipla = candidatas_multiplas.head(1)
            resultados_multiplos_finais.append(melhor_multipla)
            
            modelo_remover = melhor_multipla["MODELO"].iloc[0]
            candidatas_multiplas = candidatas_multiplas[candidatas_multiplas["MODELO"] != modelo_remover]
    
    if resultados_unicas_finais:
        df_unicas_final = pd.concat(resultados_unicas_finais, ignore_index=True)
        df_unicas_final = df_unicas_final.drop(columns=['ERRO_PRESSAO_ABS', 'ABS_ERRO_RELATIVO', 'PRIORIDADE_TIPO'], errors='ignore')
    else:
        df_unicas_final = pd.DataFrame()
    
    if resultados_multiplos_finais:
        df_multiplas_final = pd.concat(resultados_multiplos_finais, ignore_index=True)
        df_multiplas_final = df_multiplas_final.drop(columns=['ERRO_PRESSAO_ABS', 'ABS_ERRO_RELATIVO', 'PRIORIDADE_TIPO'], errors='ignore')
    else:
        df_multiplas_final = pd.DataFrame()
        
    return df_unicas_final, df_multiplas_final

# ===================================================================
# FUNÇÃO PARA EXIBIR RESULTADOS DE BUSCA (COM BOTÃO DE DOWNLOAD DO GRÁFICO)
# ===================================================================
def exibir_resultados_busca(T, key_prefix):
    """Função dedicada a exibir a tabela de resultados e documentos da busca de bombas."""
    resultado = (st.session_state.get('resultado_sistemas_multiplos', pd.DataFrame()) 
                 if st.session_state.get('modo_visualizacao') == 'multiplas' 
                 else st.session_state.get('resultado_bombas_unicas', pd.DataFrame()))

    st.header(T['results_header'])
    
    with st.container(border=True):
        tem_unicas = not st.session_state.get('resultado_bombas_unicas', pd.DataFrame()).empty
        tem_multiplas = not st.session_state.get('resultado_sistemas_multiplos', pd.DataFrame()).empty
        
        if tem_unicas or tem_multiplas:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(T['show_unique_button'], use_container_width=True, disabled=not tem_unicas or st.session_state.modo_visualizacao == 'unicas', key=f"{key_prefix}_btn_unicas"):
                    st.session_state.modo_visualizacao = 'unicas'
                    st.rerun()
            with col2:
                if st.button(T['show_systems_button'], use_container_width=True, disabled=not tem_multiplas or st.session_state.modo_visualizacao == 'multiplas', key=f"{key_prefix}_btn_multiplas"):
                    st.session_state.modo_visualizacao = 'multiplas'
                    st.rerun()

        if resultado.empty:
            if st.session_state.get('modo_visualizacao') == 'unicas': st.error(T['no_unique_pumps'])
            else: st.error(T['no_systems_found'])
        else:
            # ... (O CÓDIGO DA TABELA CONTINUA IGUAL, NÃO PRECISA MUDAR) ...
            resultado_exibicao = resultado.copy()
            def traduzir_tipo_sistema(row):
                code = row.get('TIPO_SISTEMA_CODE', 'single')
                if code == "single": return T['system_type_single']
                if code == "parallel": return T['system_type_parallel'].format(int(row.get('N_TOTAL_BOMBAS', 2)))
                if code == "series": return T['system_type_series']
                if code == "combined": return T['system_type_combined'].format(int(row.get('N_TOTAL_BOMBAS', 4)), int(row.get('N_PARALELO', 2)))
                return ""
            
            resultado_exibicao[T['system_type_header']] = resultado_exibicao.apply(traduzir_tipo_sistema, axis=1)
            resultado_exibicao.drop(columns=['TIPO_SISTEMA_CODE', 'N_TOTAL_BOMBAS', 'N_PARALELO'], errors='ignore', inplace=True)
            resultado_exibicao.rename(columns={
                "RENDIMENTO (%)": "RENDIMENTO", "POTÊNCIA (HP)": "POTÊNCIA", "MOTOR FINAL (CV)": "MOTOR FINAL",
                "ERRO_PRESSAO": T['pressure_error_header'], "ERRO_RELATIVO": T['relative_error_header']
            }, inplace=True)
            
            resultado_exibicao.insert(0, "Ranking", [f"{i+1}º" for i in range(len(resultado_exibicao))])
            
            opcoes_ranking = [f"{i+1}º" for i in range(len(resultado_exibicao))]
            st.radio("Selecione a bomba:", options=opcoes_ranking, index=0, horizontal=True, label_visibility="collapsed", key=f'radio_selecao_{key_prefix}_{st.session_state.modo_visualizacao}')
            
            for col in ['RENDIMENTO', 'POTÊNCIA', 'MOTOR FINAL', T['pressure_error_header'], T['relative_error_header']]:
                if col in resultado_exibicao.columns:
                    resultado_exibicao[col] = resultado_exibicao[col].map('{:,.2f}'.format)
            
            st.dataframe(resultado_exibicao, hide_index=True, use_container_width=True, column_order=['Ranking', T['system_type_header'], 'MODELO', 'ROTOR', 'RENDIMENTO', 'POTÊNCIA', 'MOTOR FINAL'])
    
    if not resultado.empty:
        st.subheader("Documentação Técnica")
        
        indice_selecionado = opcoes_ranking.index(st.session_state[f'radio_selecao_{key_prefix}_{st.session_state.modo_visualizacao}'])
        bomba_selecionada = resultado.iloc[indice_selecionado]
        modelo_selecionado = bomba_selecionada['MODELO']
        try:
            motor_alvo = int(bomba_selecionada['MOTOR FINAL (CV)'])
        except (ValueError, TypeError):
            motor_alvo = 0

        col_grafico, col_desenho = st.columns(2)

        with col_grafico:
            with st.container(border=True):
                st.header(T['graph_header'])
                frequencia_str = st.session_state.get('last_used_freq', '60Hz')
                caminho_pdf_grafico = Path(f"pdfs/{frequencia_str}/{modelo_selecionado}.pdf")
                
                # --- INÍCIO DA MUDANÇA ---
                if st.button(T['view_graph_button'], key=f"btn_grafico_{key_prefix}", use_container_width=True):
                    st.session_state.mostrar_grafico = not st.session_state.get('mostrar_grafico', False)
                
                if st.session_state.get('mostrar_grafico', False):
                    if caminho_pdf_grafico.exists():
                        # Adiciona o botão de download
                        with open(caminho_pdf_grafico, "rb") as pdf_file:
                            st.download_button(
                                label=T['download_graph_button'], 
                                data=pdf_file,
                                file_name=caminho_pdf_grafico.name,
                                mime="application/pdf",
                                use_container_width=True
                            )
                        # Mostra a pré-visualização
                        mostrar_pdf(caminho_pdf_grafico, legenda="Gráfico de Performance")
                    else:
                        st.warning("Gráfico de performance indisponível para este modelo.")
                # --- FIM DA MUDANÇA ---
        
        with col_desenho:
            # ... (O CÓDIGO DO DESENHO DIMENSIONAL CONTINUA IGUAL, NÃO PRECISA MUDAR) ...
            with st.container(border=True):
                st.header(T['drawing_header'])
                
                if st.button(T['dimensional_drawing_button'], key=f"btn_desenho_{key_prefix}", use_container_width=True):
                    st.session_state.mostrar_desenho = not st.session_state.get('mostrar_desenho', False)

                if st.session_state.get('mostrar_desenho', False):
                    desenho_base_path = Path("Desenhos")
                    caminho_desenho_final = None
                    if desenho_base_path.exists():
                        desenhos_candidatos = {int(p.stem.split('_')[1]): p for p in desenho_base_path.glob(f"{modelo_selecionado}*.pdf") if len(p.stem.split('_')) == 2 and p.stem.split('_')[1].isdigit()}
                        if desenhos_candidatos:
                            motor_mais_proximo = min(desenhos_candidatos.keys(), key=lambda m: abs(m - motor_alvo))
                            caminho_desenho_final = desenhos_candidatos[motor_mais_proximo]
                        else:
                            caminho_geral = desenho_base_path / f"{modelo_selecionado}.pdf"
                            if caminho_geral.exists():
                                caminho_desenho_final = caminho_geral
                    
                    if caminho_desenho_final:
                        with open(caminho_desenho_final, "rb") as pdf_file:
                            st.download_button(label=T['download_drawing_button'], data=pdf_file, file_name=caminho_desenho_final.name, mime="application/pdf", use_container_width=True)
                        mostrar_pdf(caminho_desenho_final, legenda="Desenho Dimensional")
                    else:
                        st.warning(T['drawing_unavailable'])
        
        with st.container(border=True):
             # ... (O CÓDIGO DA LISTA DE PEÇAS CONTINUA IGUAL, NÃO PRECISA MUDAR) ...
            st.header(T['parts_list_header'])
            if st.button(T['parts_list_button'], key=f"btn_lista_{key_prefix}", use_container_width=True):
                st.session_state.mostrar_lista_pecas = not st.session_state.get('mostrar_lista_pecas', False)

            if st.session_state.get('mostrar_lista_pecas', False):
                caminho_lista_pecas = Path(f"Lista/{modelo_selecionado}.pdf")
                if caminho_lista_pecas.exists():
                    st.info(T['parts_list_warning'])
                    with open(caminho_lista_pecas, "rb") as pdf_file:
                        st.download_button(label=T['download_parts_list_button'], data=pdf_file, file_name=caminho_lista_pecas.name, mime="application/pdf", use_container_width=True)
                    mostrar_pdf(caminho_lista_pecas, legenda="Lista de Peças")
                else:
                    st.warning(T['parts_list_unavailable'])
# ===================================================================
# INTERFACE STREAMLIT (COM DESIGN E LAYOUT REESTRUTURADOS)
# ===================================================================

# --- 1. Configurações Iniciais da Página e Estilos ---
if 'lang' not in st.session_state: st.session_state.lang = 'pt'
if 'resultado_busca' not in st.session_state: st.session_state.resultado_busca = None
if 'search_source' not in st.session_state: st.session_state.search_source = None # Para controlar a origem da busca

st.set_page_config(
    layout="wide",
    page_title="Seletor Higra Mining",
    page_icon="iconhigra.png" 
)

COR_PRIMARIA = "#134883"
COR_SECUNDARIA = "#F8AC2E"
COR_FUNDO = "#F0F5FF"
COR_TEXTO = "#333333"

st.markdown(f"""
<style>
    /* Configurações gerais */
    .stApp {{
        background-color: {COR_FUNDO};
        color: {COR_TEXTO};
    }}
    
    /* Cabeçalhos */
    h1, h2, h3 {{
        color: {COR_PRIMARIA};
    }}

    /* Botões Principais de Ação */
    .stButton>button {{
        border: 2px solid {COR_PRIMARIA};
        background-color: {COR_PRIMARIA};
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
        border-radius: 8px;
    }}
    .stButton>button:hover {{
        background-color: white;
        color: {COR_PRIMARIA};
    }}
    
    /* Alertas */
    .stAlert > div {{ border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); padding: 15px 20px; }}
    .stAlert-info {{ background-color: #e3f2fd; color: {COR_PRIMARIA}; border-left: 5px solid {COR_PRIMARIA}; }}
    .stAlert-error {{ background-color: #ffebee; color: #b71c1c; border-left: 5px solid #E74C3C; }}

    /* Containers com Borda (Cards) */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {{
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        background-color: white;
    }}

    /* Container de bandeiras */
    .bandeira-container {{ cursor: pointer; transition: all 0.2s ease-in-out; border-radius: 8px; padding: 5px; margin-top: 10px; border: 2px solid transparent; }}
    .bandeira-container:hover {{ transform: scale(1.1); background-color: rgba(19, 72, 131, 0.1); }}
    .bandeira-container.selecionada {{ border: 2px solid {COR_SECUNDARIA}; box-shadow: 0 0 10px rgba(248, 172, 46, 0.5); }}
    .bandeira-img {{ width: 45px; height: 30px; object-fit: cover; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }}

    /* Estilização das Abas (st.tabs) */
    [data-baseweb="tab-list"] {{
        gap: 8px;
        border-bottom: none !important;
        margin-bottom: 10px;
    }}
    [data-baseweb="tab-list"] button {{
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
        padding: 10px 20px !important;
        font-weight: bold;
        border: none !important;
    }}
    [data-baseweb="tab-list"] button[aria-selected="false"] {{
        background-color: #e3f2fd !important;
        color: {COR_PRIMARIA} !important;
    }}
    [data-baseweb="tab-list"] button[aria-selected="false"]:hover {{
        background-color: #d1e9fc !important;
    }}
    [data-baseweb="tab-list"] button[aria-selected="true"] {{
        background-color: {COR_PRIMARIA} !important;
        color: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        position: relative;
    }}
    [data-baseweb="tab-list"] button[aria-selected="true"]::after {{
        content: '';
        position: absolute;
        bottom: -5px;
        left: 5%;
        width: 90%;
        height: 4px;
        background-color: {COR_SECUNDARIA};
        border-radius: 2px;
    }}

    /* ========================================================================= */
    /* NOVO: Estilos específicos para os campos da CALCULADORA DE SISTEMA        */
    /* ========================================================================= */
    .calculator-container div[data-testid="stNumberInput"] > div > div,
    .calculator-container div[data-testid="stSelectbox"] > div {{
        background-color: #FFF9E9 !important; /* Fundo amarelo clarinho */
        border: 1px solid #F8AC2E !important; /* Borda amarela sutil */
        border-radius: 8px !important;
    }}

    .calculator-container div[data-testid="stNumberInput"] input {{
        background-color: transparent !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 2. Cabeçalho com Logo e Seleção de Idioma ---
query_params = st.query_params
if 'lang' in query_params:
    lang_from_url = query_params['lang']
    if lang_from_url in ['pt', 'en', 'es']:
        st.session_state.lang = lang_from_url

bandeiras = {
    "pt": {"nome": "PT", "img": "brasil.png"},
    "en": {"nome": "EN", "img": "uk.png"},
    "es": {"nome": "ES", "img": "espanha.png"}
}

# Mantém as bandeiras no canto direito superior
_, col_bandeiras = st.columns([6, 2])
with col_bandeiras:
    flag_cols = st.columns(len(bandeiras))
    for i, (lang_code, info) in enumerate(bandeiras.items()):
        with flag_cols[i]:
            classe_css = "selecionada" if st.session_state.lang == lang_code else ""
            img_base64 = image_to_base64(info["img"])
            st.markdown(f"""
            <a href="?lang={lang_code}" target="_self" style="text-decoration: none;">
                <div style="display: flex; flex-direction: column; align-items: center; font-family: 'Source Sans Pro', sans-serif; font-weight: bold; color: {COR_PRIMARIA};">
                    <span>{info['nome']}</span>
                    <div class="bandeira-container {classe_css}">
                        <img src="data:image/png;base64,{img_base64}" class="bandeira-img">
                    </div>
                </div>
            </a>
            """, unsafe_allow_html=True)

# Centraliza o Logo
col1, col_logo_centro, col3 = st.columns([2, 3, 2])
with col_logo_centro:
    st.image("logo.png", width=700)

T = TRADUCOES[st.session_state.lang]

# Centraliza os Textos
st.markdown(f"<h1 style='text-align: center;'>{T['main_title']}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center;'>{T['welcome_message']}</p>", unsafe_allow_html=True)
st.info(T['performance_note'])
st.divider()


# --- 3. Bloco de Entradas do Usuário ---
with st.container(border=True):
    # Cria as abas com base na configuração MOSTRAR_CALCULADORA
    if MOSTRAR_CALCULADORA:
        tab_seletor, tab_buscador, tab_calculadora = st.tabs([
            T['selector_tab_label'], T['finder_tab_label'], T['calculator_tab_label']
        ])
    else:
        tab_seletor, tab_buscador = st.tabs([
            T['selector_tab_label'], T['finder_tab_label']
        ])

    ARQUIVOS_DADOS = { "60Hz": "60Hz.xlsx", "50Hz": "50Hz.xlsx" }
    FATORES_VAZAO = { "m³/h": 1.0, "gpm (US)": 0.2271247, "l/s": 3.6 }
    FATORES_PRESSAO = { "mca": 1.0, "ftH₂O": 0.3048, "bar": 10.197, "kgf/cm²": 10.0 }
    
    # Aba 1: Seletor por Ponto de Trabalho
    with tab_seletor:
        st.subheader(T['input_header'])
        
        col_freq, col_vazao, col_pressao = st.columns(3)
        with col_freq:
            st.markdown(f"**{T['eletric_freq_title']}**")
            frequencia_selecionada = st.radio(T['freq_header'], list(ARQUIVOS_DADOS.keys()), horizontal=True, label_visibility="collapsed", key='freq_seletor')
        with col_vazao:
            st.markdown(T['flow_header'])
            v_col1, v_col2 = st.columns([2,1])
            with v_col1: vazao_bruta = st.number_input(T['flow_value_label'], min_value=0.1, value=100.0, step=10.0, label_visibility="collapsed", key='vazao_bruta')
            with v_col2: unidade_vazao = st.selectbox(T['flow_unit_label'], list(FATORES_VAZAO.keys()), label_visibility="collapsed", key='unidade_vazao')
        with col_pressao:
            st.markdown(T['pressure_header'])
            p_col1, p_col2 = st.columns([2,1])
            with p_col1: pressao_bruta = st.number_input(T['pressure_value_label'], min_value=0.1, value=100.0, step=5.0, label_visibility="collapsed", key='pressao_bruta')
            with p_col2: unidade_pressao = st.selectbox(T['pressure_unit_label'], list(FATORES_PRESSAO.keys()), label_visibility="collapsed", key='unidade_pressao')

        st.divider()
        vazao_para_busca = round(vazao_bruta * FATORES_VAZAO[unidade_vazao])
        pressao_para_busca = round(pressao_bruta * FATORES_PRESSAO[unidade_pressao])
        st.info(T['converted_values_info'].format(vazao=vazao_para_busca, pressao=pressao_para_busca))

        if st.button(T['search_button'], use_container_width=True, key='btn_seletor', type="primary"):
            st.session_state.search_source = 'seletor'
            st.session_state.resultado_calculadora = None # Limpa resultado da outra aba
            df_processado = carregar_e_processar_dados(ARQUIVOS_DADOS[frequencia_selecionada])
            st.session_state.last_used_freq = frequencia_selecionada
            with st.spinner(T['spinner_text'].format(freq=frequencia_selecionada)):
                bombas_unicas, sistemas_multiplos = selecionar_bombas(df_processado, vazao_para_busca, pressao_para_busca)
                st.session_state.resultado_bombas_unicas = bombas_unicas
                st.session_state.resultado_sistemas_multiplos = sistemas_multiplos
                if not bombas_unicas.empty: st.session_state.modo_visualizacao = 'unicas'
                elif not sistemas_multiplos.empty: st.session_state.modo_visualizacao = 'multiplas'
                else: st.session_state.modo_visualizacao = 'unicas'
                st.session_state.resultado_busca = True 
            st.rerun()
        
        if st.session_state.search_source == 'seletor' and st.session_state.get('resultado_busca'):
            exibir_resultados_busca(T, key_prefix='seletor')

    # Aba 2: Buscador por Modelo
    with tab_buscador:
        st.subheader(T['finder_header'])
        col_freq_busca, col_modelo_busca, col_motor_busca = st.columns(3)
        
        with col_freq_busca:
            st.markdown(f"**{T['eletric_freq_title']}**")
            frequencia_buscador = st.radio(T['freq_header'], list(ARQUIVOS_DADOS.keys()), horizontal=True, key='freq_buscador')

        df_buscador = carregar_e_processar_dados(ARQUIVOS_DADOS[frequencia_buscador])
        if df_buscador is not None:
            with col_modelo_busca:
                st.markdown(f"**{T['model_select_label']}**")
                lista_modelos = ["-"] + sorted(df_buscador['MODELO'].unique())
                modelo_selecionado_buscador = st.selectbox(T['model_select_label'], lista_modelos, key='modelo_buscador', label_visibility="collapsed")

            with col_motor_busca:
                st.markdown(f"**{T['motor_select_label']}**")
                motor_selecionado_buscador = None
                if modelo_selecionado_buscador and modelo_selecionado_buscador != "-":
                    motores_unicos = df_buscador[df_buscador['MODELO'] == modelo_selecionado_buscador]['MOTOR PADRÃO (CV)'].unique()
                    motores_disponiveis = sorted([motor for motor in motores_unicos if pd.notna(motor)])
                    if motores_disponiveis:
                        motor_selecionado_buscador = st.selectbox(T['motor_select_label'], motores_disponiveis, key='motor_buscador', label_visibility="collapsed")
                    else: st.selectbox(T['motor_select_label'], ["-"], disabled=True, label_visibility="collapsed")
                else: st.selectbox(T['motor_select_label'], ["-"], disabled=True, label_visibility="collapsed")

            st.divider()
            if modelo_selecionado_buscador and modelo_selecionado_buscador != "-" and motor_selecionado_buscador:
                if st.button(T['find_pump_button'], use_container_width=True, key='btn_find_pump', type="primary"):
                    st.session_state.search_source = 'buscador'
                    st.session_state.resultado_calculadora = None # Limpa resultado da outra aba
                    st.session_state.last_used_freq = frequencia_buscador
                    resultado = buscar_por_modelo_e_motor(df_buscador, modelo_selecionado_buscador, motor_selecionado_buscador)
                    if not resultado.empty:
                        st.session_state.resultado_bombas_unicas = resultado
                        st.session_state.resultado_sistemas_multiplos = pd.DataFrame()
                        st.session_state.modo_visualizacao = 'unicas'
                        st.session_state.resultado_busca = True
                    else:
                        st.session_state.resultado_busca = None
                        st.error(T['no_solution_error'])
                    st.rerun()

        if st.session_state.search_source == 'buscador' and st.session_state.get('resultado_busca'):
            exibir_resultados_busca(T, key_prefix='buscador')

    # Aba 3: Calculadora de Sistema
    if MOSTRAR_CALCULADORA:
     with tab_calculadora:
        st.subheader(T['calculator_header'])
        st.write(T['calculator_intro'])
        st.write("---")
        
        if 'resultado_calculadora' not in st.session_state:
            st.session_state.resultado_calculadora = None

        FATORES_TEMP = {"°C": 1.0, "°F": 0.5556}
        FATORES_COMPRIMENTO = {"m": 1.0, "ft": 0.3048}
        FATORES_DIAMETRO = {"mm": 1.0, "in": 25.4}

        with st.container(border=True):
            st.markdown(f"**{T['section_general_data']}**")
            col_freq_calc, col_vazao_calc, col_temp_calc = st.columns(3)
            with col_freq_calc:
                 st.markdown(f"**{T['eletric_freq_title']}**")
                 frequencia_calculadora = st.radio(T['freq_header'], list(ARQUIVOS_DADOS.keys()), horizontal=True, label_visibility="collapsed", key='freq_calc')
            with col_vazao_calc:
                st.markdown(T['desired_flow_rate'])
                c1, c2 = st.columns([2,1])
                with c1: vazao_req_bruta = st.number_input("Vazão", min_value=0.1, value=100.0, step=10.0, label_visibility="collapsed", key='vazao_req_bruta')
                with c2: unidade_vazao_req = st.selectbox("Unidade Vazão", list(FATORES_VAZAO.keys()), label_visibility="collapsed", key='unidade_vazao_req')
            with col_temp_calc:
                st.markdown(T['fluid_temperature'])
                c1, c2 = st.columns([2,1])
                with c1: temp_fluido_bruta = st.number_input("Temperatura", value=20, label_visibility="collapsed", key='temp_fluido_bruta')
                with c2: unidade_temp = st.selectbox("Unidade Temp", ["°C", "°F"], label_visibility="collapsed", key='unidade_temp')

        with st.container(border=True):
            st.markdown(f"**{T['section_piping']}**")
            col_mat, col_diam, col_comp = st.columns(3)
            with col_mat:
                st.markdown(T['pipe_material'])
                materiais_map = {
                    T['pipe_material_cs']: 'cs', T['pipe_material_ss']: 'ss',
                    T['pipe_material_di']: 'di', T['pipe_material_ci']: 'ci',
                    T['pipe_material_pvc']: 'pvc', T['pipe_material_hdpe']: 'hdpe',
                }
                material_display = st.selectbox("Material", options=list(materiais_map.keys()), label_visibility="collapsed", key='mat_tubo')
                material_tubo_key = materiais_map[material_display]
            with col_diam:
                st.markdown(T['pipe_diameter'])
                c1, c2 = st.columns([2,1])
                with c1: diametro_tubo_bruto = st.number_input("Diâmetro", min_value=1.0, value=150.0, step=1.0, label_visibility="collapsed", key='diam_tubo_bruto')
                with c2: unidade_diametro = st.selectbox("Unidade Diâmetro", list(FATORES_DIAMETRO.keys()), label_visibility="collapsed", key='unidade_diam')
            with col_comp:
                st.markdown(T['pipe_length'])
                c1, c2 = st.columns([2,1])
                with c1: comprimento_tubo_bruto = st.number_input("Comprimento", min_value=0.1, value=100.0, step=5.0, label_visibility="collapsed", key='comp_tubo_bruto')
                with c2: unidade_comprimento = st.selectbox("Unidade Comprimento", list(FATORES_COMPRIMENTO.keys()), label_visibility="collapsed", key='unidade_comp')

        with st.container(border=True):
            st.markdown(f"**{T['section_elevation']}**")
            col_succao, col_recalque = st.columns(2)
            with col_succao:
                st.markdown(T['suction_elevation'])
                c1, c2 = st.columns([2,1])
                with c1: alt_succao_bruta = st.number_input("Sucção", value=2.0, step=0.5, label_visibility="collapsed", key='alt_succao_bruta')
                with c2: unidade_alt_succao = st.selectbox("Unidade Altura Sucção", list(FATORES_COMPRIMENTO.keys()), label_visibility="collapsed", key='unidade_alt_s')
            with col_recalque:
                st.markdown(T['discharge_elevation'])
                c1, c2 = st.columns([2,1])
                with c1: alt_recalque_bruta = st.number_input("Recalque", value=30.0, step=1.0, label_visibility="collapsed", key='alt_recalque_bruta')
                with c2: unidade_alt_recalque = st.selectbox("Unidade Altura Recalque", list(FATORES_COMPRIMENTO.keys()), label_visibility="collapsed", key='unidade_alt_r')
            st.caption(T['elevation_help'])

        with st.container(border=True):
            st.markdown(f"**{T['section_fittings']}**")
            col_ac1, col_ac2, col_ac3, col_ac4 = st.columns(4)
            with col_ac1:
                qtd_cotovelo90 = st.number_input(T['elbow_90'], min_value=0, value=0, step=1, key='qtd_c90')
            with col_ac2:
                qtd_cotovelo45 = st.number_input(T['elbow_45'], min_value=0, value=0, step=1, key='qtd_c45')
            with col_ac3:
                qtd_valv_gaveta = st.number_input(T['gate_valve'], min_value=0, value=1, step=1, key='qtd_vg')
            with col_ac4:
                qtd_valv_retencao = st.number_input(T['check_valve'], min_value=0, value=1, step=1, key='qtd_vr')

        st.write("") 
        
        if st.button(T['calculate_button'], use_container_width=True, key='btn_calc', type="primary"):
            st.session_state.search_source = 'calculadora'
            st.session_state.resultado_busca = None

            temp_c = (temp_fluido_bruta - 32) * FATORES_TEMP[unidade_temp] if unidade_temp == '°F' else temp_fluido_bruta
            dados_para_calculo = {
                'vazao_m3h': vazao_req_bruta * FATORES_VAZAO[unidade_vazao_req],
                'temperatura_c': temp_c, 'material_key': material_tubo_key,
                'diametro_mm': diametro_tubo_bruto * FATORES_DIAMETRO[unidade_diametro],
                'comprimento_m': comprimento_tubo_bruto * FATORES_COMPRIMENTO[unidade_comprimento],
                'alt_succao_m': alt_succao_bruta * FATORES_COMPRIMENTO[unidade_alt_succao],
                'alt_recalque_m': alt_recalque_bruta * FATORES_COMPRIMENTO[unidade_alt_recalque],
                'qtd_cotovelo90': qtd_cotovelo90, 'qtd_cotovelo45': qtd_cotovelo45,
                'qtd_valv_gaveta': qtd_valv_gaveta, 'qtd_valv_retencao': qtd_valv_retencao
            }
            try:
                amt_calculada, vazao_calculada = calcular_ponto_trabalho(dados_para_calculo)
                st.session_state.resultado_calculadora = {"vazao": vazao_calculada, "pressao": amt_calculada}
            except Exception as e:
                st.error(f"Ocorreu um erro no cálculo: {e}")
                st.session_state.resultado_calculadora = None
            st.rerun()

        if st.session_state.search_source == 'calculadora' and st.session_state.resultado_calculadora:
            st.write("---")
            st.subheader(T['results_header_calculator'])
            resultado = st.session_state.resultado_calculadora
            
            col1, col2 = st.columns(2)
            col1.metric(label=T['flow_header'].replace('*',''), value=f"{resultado['vazao']:.2f} m³/h")
            col2.metric(label=T['pressure_header'].replace('*',''), value=f"{resultado['pressao']:.2f} mca")

            if st.button(T['search_with_data_button'], use_container_width=True, key="btn_calc_search"):
                df_processado = carregar_e_processar_dados(ARQUIVOS_DADOS[frequencia_calculadora])
                vazao_para_busca = round(resultado['vazao'])
                pressao_para_busca = round(resultado['pressao'])
                st.session_state.last_used_freq = frequencia_calculadora
                
                with st.spinner(T['spinner_text'].format(freq=frequencia_calculadora)):
                    bombas_unicas, sistemas_multiplos = selecionar_bombas(df_processado, vazao_para_busca, pressao_para_busca)
                    st.session_state.resultado_bombas_unicas = bombas_unicas
                    st.session_state.resultado_sistemas_multiplos = sistemas_multiplos
                    if not bombas_unicas.empty: st.session_state.modo_visualizacao = 'unicas'
                    elif not sistemas_multiplos.empty: st.session_state.modo_visualizacao = 'multiplas'
                    else: st.session_state.modo_visualizacao = 'unicas'
                    st.session_state.resultado_busca = True
                st.rerun()
        
        if st.session_state.search_source == 'calculadora' and st.session_state.get('resultado_busca'):
             exibir_resultados_busca(T, key_prefix='calculadora')
             
st.divider()
st.markdown(
    f"""
    <p style='text-align: center; color: grey;'>
        {T['footer_copyright']}<br>
        {T['footer_more_info']}<a href='https://www.higramining.com.br' target='_blank'>{T['footer_our_website']}</a>.
    </p>
    """,
    unsafe_allow_html=True
)           
