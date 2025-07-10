import streamlit as st
import fitz  # PyMuPDF
import re
import io

# -------------------------------------------------------------------
# AQUI COLOCAMOS NOSSAS FUNÇÕES DE CHECAGEM (A LÓGICA DO BACK-END)
# -------------------------------------------------------------------

def checar_regra_eixo_bruto(texto_completo_pdf):
    texto_lower = texto_completo_pdf.lower()
    texto_normalizado = re.sub(r'\s+', ' ', texto_lower)
    match = re.search(r"(eixo bruto|eixo motriz).*?(\d+)[sl]", texto_normalizado)
    if not match: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": "A expressão 'eixo bruto' ou 'eixo motriz' seguida de um número e S/L não foi encontrada." }
    numero_eixo = int(match.group(2))
    if numero_eixo >= 225:
        tem_ranhurado = "grafite ranhurado" in texto_normalizado
        tem_liso = "grafite liso" in texto_normalizado
        if tem_ranhurado and tem_liso: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "OK", "detalhes": f"Eixo ({numero_eixo}) >= 225. 'Grafite ranhurado' e 'Grafite liso' encontrados como esperado." }
        else:
            erros = []
            if not tem_ranhurado: erros.append("'grafite ranhurado' não foi encontrado")
            if not tem_liso: erros.append("'grafite liso' não foi encontrado")
            return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) >= 225. Erro: {', '.join(erros)}." }
    else:
        tem_liso = "grafite liso" in texto_normalizado
        if not tem_liso: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "OK", "detalhes": f"Eixo ({numero_eixo}) < 225. 'Grafite liso' não foi encontrado, como esperado." }
        else: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) < 225. Erro: 'Grafite liso' foi encontrado, o que não é permitido." }

def checar_regra_exportacao(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Embalagem de Exportação", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada. Não foi possível verificar a regra." }
    string_config = match_config.group(1)
    if "EMB EXPORTACAO" in string_config.upper():
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "propilenoglicol" in texto_normalizado: return { "regra": "Embalagem de Exportação", "status": "OK", "detalhes": "É uma embalagem de exportação e a menção a 'Propilenoglicol' foi encontrada corretamente." }
        else: return { "regra": "Embalagem de Exportação", "status": "FALHA", "detalhes": "É uma embalagem de exportação, mas a menção a 'Propilenoglicol' NÃO foi encontrada." }
    else: return { "regra": "Embalagem de Exportação", "status": "OK", "detalhes": "Não é uma embalagem de exportação. Regra não aplicável." }

def _criar_checador_presenca_obrigatoria(nome_regra, termo_busca):
    def checador(texto_completo_pdf):
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if termo_busca.lower() in texto_normalizado: return {"regra": nome_regra, "status": "OK", "detalhes": f"O termo obrigatório '{termo_busca}' foi encontrado."}
        else: return {"regra": nome_regra, "status": "FALHA", "detalhes": f"O termo obrigatório '{termo_busca}' NÃO foi encontrado."}
    return checador

def _criar_checador_contagem_obrigatoria(nome_regra, termo_busca):
    def checador(texto_completo_pdf):
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        ocorrencias = re.findall(termo_busca.lower(), texto_normalizado)
        contagem = len(ocorrencias)
        if contagem > 0: return {"regra": nome_regra, "status": "OK", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vez(es)."}
        else: return {"regra": nome_regra, "status": "FALHA", "detalhes": f"O termo obrigatório '{termo_busca}' NÃO foi encontrado."}
    return checador

def _buscar_gatilho_generico(config_normalizada, lista_de_gatilhos):
    for gatilho in lista_de_gatilhos:
        pattern = r"\b" + re.escape(gatilho.upper()) + r"\b"
        if re.search(pattern, config_normalizada): return gatilho
    return None

def checar_regra_sensores_protetor(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Sensores vs Protetor de Emendas", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada." }
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos = ["SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if sensor_ativado:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "protetor das emendas" in texto_normalizado: return { "regra": "Sensores vs Protetor de Emendas", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Protetor das emendas' encontrado como esperado." }
        else: return { "regra": "Sensores vs Protetor de Emendas", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'protetor das emendas' NÃO foi encontrado." }
    else: return { "regra": "Sensores vs Protetor de Emendas", "status": "OK", "detalhes": "Nenhum sensor aplicável ('SIM') foi encontrado. Regra não aplicável." }

def checar_regra_sensores_cabo_shield(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada." }
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos = ["SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if sensor_ativado:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "cabo sensor shield" in texto_normalizado: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Cabo sensor Shield' encontrado como esperado." }
        else: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'cabo sensor Shield' NÃO foi encontrado." }
    else: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "OK", "detalhes": "Nenhum sensor aplicável ('SIM') foi encontrado. Regra não aplicável." }

def checar_regra_pistao_agua_limpa(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Pistão Equalizador vs Plaqueta Água Limpa", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada." }
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).lower())
    if "pistao equalizador" in config_normalizada:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "plaqueta agua limpa" in texto_normalizado: return { "regra": "Pistão Equalizador vs Plaqueta Água Limpa", "status": "OK", "detalhes": "'Pistão equalizador' presente na config. 'Plaqueta agua limpa' encontrada como esperado." }
        else: return { "regra": "Pistão Equalizador vs Plaqueta Água Limpa", "status": "FALHA", "detalhes": "'Pistão equalizador' presente na config, mas 'plaqueta agua limpa' NÃO foi encontrada." }
    else: return { "regra": "Pistão Equalizador vs Plaqueta Água Limpa", "status": "OK", "detalhes": "'Pistão equalizador' não presente na config. Regra não aplicável." }

def checar_regra_controlador_novus(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificação Controlador Novus", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada."}
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos_and = ["1 SENS TEMP RTD", "SENSOR DE NIVEL NAO", "SENSOR ROTACAO NAO", "SENSOR TEMP MAN T NAO", "VIBRACAO NAO"]
    trigger_ok = all(termo in config_normalizada for termo in gatilhos_and)
    if trigger_ok:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "controlador de temperatura novus" in texto_normalizado: return {"regra": "Verificação Controlador Novus", "status": "OK", "detalhes": "Combinação de sensores 'NAO' encontrada. 'Controlador de temperatura novus' presente como esperado."}
        else: return {"regra": "Verificação Controlador Novus", "status": "FALHA", "detalhes": "Combinação de sensores 'NAO' encontrada, mas 'controlador de temperatura novus' NÃO foi encontrado."}
    else: return {"regra": "Verificação Controlador Novus", "status": "OK", "detalhes": "A combinação específica de sensores para esta regra não foi encontrada. Regra não aplicável."}

def checar_regra_fieldlogger(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificação Fieldlogger", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada."}
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos_fieldlogger = ["3 SENS TEMP RTD", "SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos_fieldlogger)
    if sensor_ativado:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "fieldlogger" in texto_normalizado or "field logger" in texto_normalizado: return {"regra": "Verificação Fieldlogger", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Fieldlogger' presente como esperado."}
        else: return {"regra": "Verificação Fieldlogger", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'Fieldlogger' NÃO foi encontrado."}
    else: return {"regra": "Verificação Fieldlogger", "status": "OK", "detalhes": "Nenhum sensor aplicável para esta regra foi encontrado. Regra não aplicável."}

def checar_regra_chassi_modelos(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificação de Chassi", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada."}
    string_config_original = match_config.group(1)
    config_pesquisavel = string_config_original.replace('#', ' ').upper()
    config_normalizada = re.sub(r'\s+', ' ', config_pesquisavel)
    gatilhos = ["EMB EXPORTACAO", "R 3 360", "R 3 365", "M 2 345", "R 2 390", "R 5", "R 4"]
    gatilho_encontrado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if gatilho_encontrado:
        texto_normalizado_doc = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        if "chassi" in texto_normalizado_doc: return {"regra": "Verificação de Chassi", "status": "OK", "detalhes": f"Gatilho '{gatilho_encontrado}' encontrado na config. O termo 'chassi' foi encontrado como esperado."}
        else: return {"regra": "Verificação de Chassi", "status": "FALHA", "detalhes": f"Gatilho '{gatilho_encontrado}' encontrado na config, mas o termo 'chassi' NÃO foi encontrado."}
    else: return {"regra": "Verificação de Chassi", "status": "OK", "detalhes": "Nenhum modelo ou condição aplicável para esta regra foi encontrado. Regra não aplicável."}

def checar_regra_bujao_modificada(texto_completo_pdf):
    inox_check_requerido = False
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if match_config:
        string_config = match_config.group(1)
        valores = string_config.split('#')
        if len(valores) > 9 and valores[9].upper() == "ROT INOX316":
            inox_check_requerido = True
    termo_bujao = 'bujao bsp 1"'
    linhas_com_bujao = []
    for i, linha in enumerate(texto_completo_pdf.splitlines()):
        if termo_bujao in linha.lower():
            linhas_com_bujao.append({'texto': linha, 'num_linha': i + 1})
    if not linhas_com_bujao:
        return {"regra": "Verificação de Bujão", "status": "FALHA", "detalhes": f"O termo obrigatório '{termo_bujao}' NÃO foi encontrado no documento."}
    if inox_check_requerido:
        for linha_info in linhas_com_bujao:
            if "inox316" not in linha_info['texto'].lower():
                return { "regra": "Verificação de Bujão", "status": "FALHA", "detalhes": f"Rotor é INOX316, mas a linha {linha_info['num_linha']} contém '{termo_bujao}' SEM a especificação 'inox316'." }
        return { "regra": "Verificação de Bujão", "status": "OK", "detalhes": f"Rotor é INOX316. Encontrado(s) {len(linhas_com_bujao)} bujão(ões) e todos contêm 'inox316' como esperado." }
    else:
        return { "regra": "Verificação de Bujão", "status": "OK", "detalhes": f"Rotor não é INOX316. Encontrado(s) {len(linhas_com_bujao)} bujão(ões) no documento." }

# --- NOVAS REGRAS ADICIONADAS AQUI ---
def checar_regra_tubo_termocontratil_potencia(texto_completo_pdf):
    """Verifica a presença de 'TUBO TERMOCONTRATIL 1/2"' com base na potência."""
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Tubo Termocontrátil vs Potência", "status": "FALHA", "detalhes": "A linha 'Config...........:' não foi encontrada."}
    
    string_config = match_config.group(1)
    valores = string_config.split('#')
    
    # O campo da Potência é o 6º item (índice 5)
    if len(valores) < 6:
        return {"regra": "Tubo Termocontrátil vs Potência", "status": "FALHA", "detalhes": "Não foi possível encontrar o campo de potência na string de configuração."}
    
    potencia_str = valores[5]
    match_potencia = re.search(r'(\d+)', potencia_str)
    
    if not match_potencia:
        return {"regra": "Tubo Termocontrátil vs Potência", "status": "FALHA", "detalhes": f"Não foi possível extrair um valor numérico do campo de potência ('{potencia_str}')."}
        
    potencia = int(match_potencia.group(1))

    if potencia > 75:
        texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
        termo_proibido = 'tubo termocontratil 1/2"'
        if termo_proibido in texto_normalizado:
            return {"regra": "Tubo Termocontrátil vs Potência", "status": "FALHA", "detalhes": f"Potência ({potencia}CV) > 75CV e o termo proibido '{termo_proibido}' foi encontrado."}
        else:
            return {"regra": "Tubo Termocontrátil vs Potência", "status": "OK", "detalhes": f"Potência ({potencia}CV) > 75CV e o termo proibido não foi encontrado, como esperado."}
    else: # Potencia <= 75
        return {"regra": "Tubo Termocontrátil vs Potência", "status": "OK", "detalhes": f"Potência ({potencia}CV) <= 75CV. A regra de restrição não se aplica."}

def checar_regra_contagem_tubo_termo(texto_completo_pdf):
    """Verifica se 'tubo termo' aparece mais de duas vezes."""
    texto_normalizado = re.sub(r'\s+', ' ', texto_completo_pdf.lower())
    termo_busca = "tubo termo"
    ocorrencias = re.findall(termo_busca, texto_normalizado)
    contagem = len(ocorrencias)
    
    if contagem > 2:
        return {"regra": "Contagem Máxima de 'Tubo Termo'", "status": "FALHA", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vezes, excedendo o limite de 2."}
    else:
        return {"regra": "Contagem Máxima de 'Tubo Termo'", "status": "OK", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vez(es), dentro do limite de 2."}

# Criando as regras de fábrica
checar_regra_plaqueta_sentido_giro = _criar_checador_presenca_obrigatoria("Presença de Plaqueta Sentido de Giro", "plaqueta sentido de giro")
checar_regra_plaqueta_identifica = _criar_checador_presenca_obrigatoria("Presença de Plaqueta de Identificação", "plaqueta identifica")
checar_regra_plaqueta_logotipo = _criar_checador_presenca_obrigatoria("Presença de Plaqueta Logotipo", "plaqueta logotipo")
checar_regra_plaqueta_guia_geral = _criar_checador_contagem_obrigatoria("Presença de Plaqueta Guia", "plaqueta guia")

# -------------------------------------------------------------------
# AQUI FICA O ORQUESTRADOR PRINCIPAL DO CHECKLIST
# -------------------------------------------------------------------
def executar_checklist_completo(texto_pdf):
    regras_a_checar = [
        checar_regra_eixo_bruto,
        checar_regra_exportacao,
        checar_regra_sensores_protetor,
        checar_regra_sensores_cabo_shield,
        _criar_checador_presenca_obrigatoria("Presença de Supressor Trifásico", "supressor trifasico"),
        checar_regra_plaqueta_sentido_giro,
        checar_regra_plaqueta_identifica,
        checar_regra_plaqueta_logotipo,
        checar_regra_plaqueta_guia_geral,
        checar_regra_pistao_agua_limpa,
        checar_regra_controlador_novus,
        checar_regra_fieldlogger,
        checar_regra_chassi_modelos,
        checar_regra_bujao_modificada,
        checar_regra_tubo_termocontratil_potencia, # <-- NOVA REGRA
        checar_regra_contagem_tubo_termo,        # <-- NOVA REGRA
    ]
    
    resultados_finais = []
    for funcao_checar in regras_a_checar:
        resultado = funcao_checar(texto_pdf)
        resultados_finais.append(resultado)
        
    return resultados_finais

# -------------------------------------------------------------------
# AQUI COMEÇA A INTERFACE GRÁFICA COM STREAMLIT (sem alterações)
# -------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Verificador de PDF")
st.title("✅ Verificador Automático de Documentos PDF")
st.write("Faça o upload do arquivo PDF para iniciar a verificação das regras de negócio.")
uploaded_file = st.file_uploader("Escolha o arquivo PDF", type="pdf")
if uploaded_file is not None:
    show_debug = st.checkbox("Mostrar texto extraído do PDF para depuração")
    if st.button("Iniciar Verificação", type="primary"):
        texto_completo = ""
        with st.spinner('Lendo e processando o PDF...'):
            try:
                pdf_bytes = uploaded_file.getvalue()
                documento = fitz.open(stream=pdf_bytes, filetype="pdf")
                for pagina in documento:
                    texto_completo += pagina.get_text()
                documento.close()
            except Exception as e:
                st.error(f"Ocorreu um erro ao processar o PDF: {e}")
        
        if texto_completo:
            if show_debug:
                st.subheader("Texto Extraído e Normalizado (para depuração)")
                texto_lower = texto_completo.lower()
                texto_normalizado = re.sub(r'\s+', ' ', texto_lower)
                st.text_area("Conteúdo:", texto_normalizado, height=250)

            resultados = executar_checklist_completo(texto_completo)

            st.subheader("Resultados da Verificação:")
            for res in resultados:
                if res['status'] == 'OK':
                    with st.expander(f"✅ {res['regra']}: OK", expanded=False):
                        st.success(f"**Status:** {res['status']}")
                        st.info(f"**Detalhes:** {res['detalhes']}")
                else:
                    with st.expander(f"❌ {res['regra']}: FALHA", expanded=True):
                        st.error(f"**Status:** {res['status']}")
                        st.warning(f"**Detalhes:** {res['detalhes']}")
