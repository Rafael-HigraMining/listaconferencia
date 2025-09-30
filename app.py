import streamlit as st
import fitz  # PyMuPDF
import re
import io
import unicodedata

st.set_page_config(layout="centered", page_title="Ferramenta Interna")
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

st.title("Analisador de Proposta Técnica 🕵️")
st.info("Esta página é de uso interno e só é visível com o link secreto.")
st.write("---")

# -------------------------------------------------------------------
# AQUI COLOCAMOS NOSSAS FUNÇÕES DE CHECAGEM (A LÓGICA DO BACK-END)
# -------------------------------------------------------------------


def _remover_acentos(texto: str) -> str:
    nfkd_form = unicodedata.normalize('NFD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def _normalizar_texto_completo(texto: str) -> str:
    texto_lower = texto.lower()
    texto_sem_acentos = _remover_acentos(texto_lower)
    texto_normalizado = re.sub(r'\s+', ' ', texto_sem_acentos)
    return texto_normalizado

def _extrair_tamanho_cabo_flexivel(texto_normalizado):
    match = re.search(r"cabo flexivel.*?(\d+)\s*mm[2²]", texto_normalizado)
    if match:
        return int(match.group(1))
    return None

def _extrair_numero_eixo(texto_normalizado):
    match = re.search(r"(eixo bruto|eixo motriz).*?(\d+)[sl]", texto_normalizado)
    if match:
        return int(match.group(2))
    return None
    
def _extrair_material_rotor(texto_completo_pdf):
    """Extrai o material do rotor a partir da string de configuração."""
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if match_config:
        string_config = match_config.group(1)
        valores = string_config.split('#')
        # Rotor é o 10º item (índice 9)
        if len(valores) > 9:
            return valores[9].upper()
    return None
    
def _extrair_potencia_config(texto_completo_pdf):
    """Extrai o valor numérico da potência a partir da string de configuração."""
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config:
        return None
    
    string_config = match_config.group(1)
    valores = string_config.split('#')
    
    # Potência é o 6º item (índice 5)
    if len(valores) > 5:
        potencia_str = valores[5]
        match_potencia = re.search(r'(\d+)', potencia_str)
        if match_potencia:
            return int(match_potencia.group(1))
    return None

# --- SUBSTITUA A FUNÇÃO ANTIGA DO EIXO POR ESTA VERSÃO ATUALIZADA ---
def checar_regra_eixo_bruto(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    numero_eixo = _extrair_numero_eixo(texto_normalizado)
    regra = "Eixo Bruto/Motriz vs Grafites"
    
    # --- A MUDANÇA COMEÇA AQUI: Adicionando a mensagem de dica ---
    msg_dica_falha = "Dica: Para carcaças >= 225S, o correto e: Anel de Grafite Liso + Anel de Aco Ranhurado Simples + Anel de Grafite Ranhurado. Para carcaças < 225S, o correto e: Anel de Grafite Ranhurado dos dois lados + Anel de Aco Liso."

    if not numero_eixo:
        return { "regra": regra, "status": "FALHA", "detalhes": f"A expressao 'eixo bruto' ou 'eixo motriz' seguida de um numero e S/L nao foi encontrada. {msg_dica_falha}" }
    
    if numero_eixo >= 225:
        tem_ranhurado = "grafite ranhurado" in texto_normalizado
        tem_liso = "grafite liso" in texto_normalizado
        if tem_ranhurado and tem_liso:
            return { "regra": regra, "status": "OK", "detalhes": f"Eixo ({numero_eixo}) >= 225. 'Grafite ranhurado' e 'Grafite liso' encontrados como esperado." }
        else:
            erros = []
            if not tem_ranhurado: erros.append("'grafite ranhurado' nao foi encontrado")
            if not tem_liso: erros.append("'grafite liso' nao foi encontrado")
            return { "regra": regra, "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) >= 225. Erro: {', '.join(erros)}. {msg_dica_falha}" }
    else: # numero_eixo < 225
        tem_liso = "grafite liso" in texto_normalizado
        if not tem_liso:
            return { "regra": regra, "status": "OK", "detalhes": f"Eixo ({numero_eixo}) < 225. 'Grafite liso' nao foi encontrado, como esperado." }
        else:
            return { "regra": regra, "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) < 225. Erro: 'Grafite liso' foi encontrado, o que nao e permitido. {msg_dica_falha}" }

def checar_regra_exportacao(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Embalagem de Exportacao", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada." }
    string_config = match_config.group(1)
    if "EMB EXPORTACAO" in string_config.upper():
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "propilenoglicol" in texto_normalizado: return { "regra": "Embalagem de Exportacao", "status": "OK", "detalhes": "E uma embalagem de exportacao e a mencao a 'Propilenoglicol' foi encontrada corretamente." }
        else: return { "regra": "Embalagem de Exportacao", "status": "FALHA", "detalhes": "E uma embalagem de exportacao, mas a mencao a 'Propilenoglicol' NAO foi encontrada." }
    else: return { "regra": "Embalagem de Exportacao", "status": "OK", "detalhes": "Nao e uma embalagem de exportacao. Regra nao aplicavel." }

def _criar_checador_presenca_obrigatoria(nome_regra, termo_busca):
    def checador(texto_completo_pdf):
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        termo_busca_normalizado = _remover_acentos(termo_busca.lower())
        if termo_busca_normalizado in texto_normalizado: return {"regra": nome_regra, "status": "OK", "detalhes": f"O termo obrigatorio '{termo_busca}' foi encontrado."}
        else: return {"regra": nome_regra, "status": "FALHA", "detalhes": f"O termo obrigatorio '{termo_busca}' NAO foi encontrado."}
    return checador

def _criar_checador_contagem_obrigatoria(nome_regra, termo_busca):
    def checador(texto_completo_pdf):
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        termo_busca_normalizado = _remover_acentos(termo_busca.lower())
        ocorrencias = re.findall(termo_busca_normalizado, texto_normalizado)
        contagem = len(ocorrencias)
        if contagem > 0: return {"regra": nome_regra, "status": "OK", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vez(es)."}
        else: return {"regra": nome_regra, "status": "FALHA", "detalhes": f"O termo obrigatorio '{termo_busca}' NAO foi encontrado."}
    return checador

def _buscar_gatilho_generico(config_normalizada, lista_de_gatilhos):
    for gatilho in lista_de_gatilhos:
        pattern = r"\b" + re.escape(gatilho.upper()) + r"\b"
        if re.search(pattern, config_normalizada): return gatilho
    return None

def checar_regra_sensores_protetor(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Sensores vs Protetor de Emendas", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada." }
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos = ["SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if sensor_ativado:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "protetor das emendas" in texto_normalizado: return { "regra": "Sensores vs Protetor de Emendas", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Protetor das emendas' encontrado como esperado." }
        else: return { "regra": "Sensores vs Protetor de Emendas", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'protetor das emendas' NAO foi encontrado." }
    else: return { "regra": "Sensores vs Protetor de Emendas", "status": "OK", "detalhes": "Nenhum sensor aplicavel ('SIM') foi encontrado. Regra nao aplicavel." }

def checar_regra_sensores_cabo_shield(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada." }
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos = ["SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if sensor_ativado:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "cabo sensor shield" in texto_normalizado: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Cabo sensor Shield' encontrado como esperado." }
        else: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'cabo sensor Shield' NAO foi encontrado." }
    else: return { "regra": "Sensores vs Cabo Sensor Shield", "status": "OK", "detalhes": "Nenhum sensor aplicavel ('SIM') foi encontrado. Regra nao aplicavel." }

def checar_regra_pistao_agua_limpa(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return { "regra": "Pistao Equalizador vs Plaqueta Agua Limpa", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada." }
    config_normalizada = _normalizar_texto_completo(match_config.group(1))
    if "pistao equalizador" in config_normalizada:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "plaqueta agua limpa" in texto_normalizado: return { "regra": "Pistao Equalizador vs Plaqueta Agua Limpa", "status": "OK", "detalhes": "'Pistao equalizador' presente na config. 'Plaqueta agua limpa' encontrada como esperado." }
        else: return { "regra": "Pistao Equalizador vs Plaqueta Agua Limpa", "status": "FALHA", "detalhes": "'Pistao equalizador' presente na config, mas 'plaqueta agua limpa' NAO foi encontrada." }
    else: return { "regra": "Pistao Equalizador vs Plaqueta Agua Limpa", "status": "OK", "detalhes": "'Pistao equalizador' nao presente na config. Regra nao aplicavel." }

def checar_regra_controlador_novus(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificacao Controlador Novus", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada."}
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos_and = ["1 SENS TEMP RTD", "SENSOR DE NIVEL NAO", "SENSOR ROTACAO NAO", "SENSOR TEMP MAN T NAO", "VIBRACAO NAO"]
    trigger_ok = all(termo in config_normalizada for termo in gatilhos_and)
    if trigger_ok:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "controlador de temperatura novus" in texto_normalizado: return {"regra": "Verificacao Controlador Novus", "status": "OK", "detalhes": "Combinacao de sensores 'NAO' encontrada. 'Controlador de temperatura novus' presente como esperado."}
        else: return {"regra": "Verificacao Controlador Novus", "status": "FALHA", "detalhes": "Combinacao de sensores 'NAO' encontrada, mas 'controlador de temperatura novus' NAO foi encontrado."}
    else: return {"regra": "Verificacao Controlador Novus", "status": "OK", "detalhes": "A combinacao especifica de sensores para esta regra nao foi encontrada. Regra nao aplicavel."}

def checar_regra_fieldlogger(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificacao Fieldlogger", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada."}
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    gatilhos_fieldlogger = ["3 SENS TEMP RTD", "SENSOR DE NIVEL SIM", "SENSOR ROTACAO SIM", "SENSOR TEMP MAN T SIM", "VIBRACAO SIM"]
    sensor_ativado = _buscar_gatilho_generico(config_normalizada, gatilhos_fieldlogger)
    if sensor_ativado:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        if "fieldlogger" in texto_normalizado or "field logger" in texto_normalizado: return {"regra": "Verificacao Fieldlogger", "status": "OK", "detalhes": f"Gatilho '{sensor_ativado}' encontrado. 'Fieldlogger' presente como esperado."}
        else: return {"regra": "Verificacao Fieldlogger", "status": "FALHA", "detalhes": f"Gatilho '{sensor_ativado}' encontrado, mas 'Fieldlogger' NÃO foi encontrado."}
    else: return {"regra": "Verificacao Fieldlogger", "status": "OK", "detalhes": "Nenhum sensor aplicavel para esta regra foi encontrado. Regra nao aplicavel."}

def checar_regra_chassi_modelos(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Verificacao de Chassi", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada."}
    string_config_original = match_config.group(1)
    config_pesquisavel = string_config_original.replace('#', ' ').upper()
    config_normalizada = re.sub(r'\s+', ' ', config_pesquisavel)
    gatilhos = ["EMB EXPORTACAO", "R 3 360", "R 3 365", "M 2 345", "R 2 390", "R 5", "R 4"]
    gatilho_encontrado = _buscar_gatilho_generico(config_normalizada, gatilhos)
    if gatilho_encontrado:
        texto_normalizado_doc = _normalizar_texto_completo(texto_completo_pdf)
        if "chassi" in texto_normalizado_doc: return {"regra": "Verificacao de Chassi", "status": "OK", "detalhes": f"Gatilho '{gatilho_encontrado}' encontrado na config. O termo 'chassi' foi encontrado como esperado."}
        else: return {"regra": "Verificacao de Chassi", "status": "FALHA", "detalhes": f"Gatilho '{gatilho_encontrado}' encontrado na config, mas o termo 'chassi' NÃO foi encontrado."}
    else: return {"regra": "Verificacao de Chassi", "status": "OK", "detalhes": "Nenhum modelo ou condicao aplicavel para esta regra foi encontrado. Regra nao aplicavel."}

def checar_regra_bujao_modificada(texto_completo_pdf):
    """
    Busca por 'BUJAO BSP 1"' e, se o rotor for inox316/aisi316/cd4mcun,
    valida se 'inox316' está na mesma linha.
    """
    inox_check_requerido = False
    material_rotor = _extrair_material_rotor(texto_completo_pdf)
    
    if material_rotor:
        gatilhos_inox = ("ROT INOX316", "ROT AISI316", "ROT CD4MCUN")
        if material_rotor.startswith(gatilhos_inox):
            inox_check_requerido = True

    termo_bujao = 'bujao bsp 1"'
    linhas_com_bujao = []
    for i, linha in enumerate(texto_completo_pdf.splitlines()):
        if termo_bujao in linha.lower():
            linhas_com_bujao.append({'texto': linha, 'num_linha': i + 1})

    if not linhas_com_bujao:
        return {"regra": "Verificacao de Bujao", "status": "FALHA", "detalhes": f"O termo obrigatorio '{termo_bujao}' NAO foi encontrado no documento."}

    if inox_check_requerido:
        for linha_info in linhas_com_bujao:
            if "inox316" not in linha_info['texto'].lower():
                return { "regra": "Verificacao de Bujao", "status": "FALHA", "detalhes": f"Rotor e de material especial ({material_rotor}), mas a linha {linha_info['num_linha']} contem '{termo_bujao}' SEM a especificacao 'inox316'." }
        return { "regra": "Verificacao de Bujao", "status": "OK", "detalhes": f"Rotor e de material especial ({material_rotor}). Encontrado(s) {len(linhas_com_bujao)} bujao(oes) e todos contem 'inox316' como esperado." }
    else:
        return { "regra": "Verificacao de Bujao", "status": "OK", "detalhes": f"Rotor nao e de material especial. Encontrado(s) {len(linhas_com_bujao)} bujao(oes) no documento." }

def checar_regra_tubo_termocontratil_potencia(texto_completo_pdf):
    """Verifica a presença de 'TUBO TERMOCONTRATIL 1/2"' com base na potência."""
    potencia = _extrair_potencia_config(texto_completo_pdf)
    regra = "Tubo Termocontratil vs Potencia"

    if potencia is None:
        return {"regra": regra, "status": "FALHA", "detalhes": "Nao foi possivel extrair a potencia da string de configuracao."}

    if potencia > 75:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        termo_proibido = 'tubo termocontratil 1/2"'
        if termo_proibido in texto_normalizado:
            return {"regra": regra, "status": "FALHA", "detalhes": f"Potencia ({potencia}CV) > 75CV e o termo proibido '{termo_proibido}' foi encontrado."}
        else:
            return {"regra": regra, "status": "OK", "detalhes": f"Potencia ({potencia}CV) > 75CV e o termo proibido nao foi encontrado, como esperado."}
    else: # Potencia <= 75
        return {"regra": regra, "status": "OK", "detalhes": f"Potencia ({potencia}CV) <= 75CV. A regra de restricao nao se aplica."}

def checar_regra_contagem_tubo_termo(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    termo_busca = "tubo termo"
    ocorrencias = re.findall(termo_busca, texto_normalizado)
    contagem = len(ocorrencias)
    if contagem > 2:
        return {"regra": "Contagem Maxima de 'Tubo Termo'", "status": "FALHA", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vezes, excedendo o limite de 2."}
    else:
        return {"regra": "Contagem Maxima de 'Tubo Termo'", "status": "OK", "detalhes": f"O termo '{termo_busca}' foi encontrado {contagem} vez(es), dentro do limite de 2."}

def checar_regra_sensor_nivel_itens(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config:
        return {"regra": "Itens para Sensor de Nivel", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada."}
    config_normalizada = re.sub(r'\s+', ' ', match_config.group(1).upper())
    if "SENSOR DE NIVEL SIM" in config_normalizada:
        texto_normalizado_doc = _normalizar_texto_completo(texto_completo_pdf)
        itens_obrigatorios = ["flange dos sensores", "suporte do sensor", "sensor fotoeletrico", "prensa cabo bsp"]
        itens_faltando = []
        for item in itens_obrigatorios:
            if item not in texto_normalizado_doc:
                itens_faltando.append(item)
        if not itens_faltando:
            itens_encontrados_str = ", ".join(itens_obrigatorios)
            return {"regra": "Itens para Sensor de Nivel", "status": "OK", "detalhes": f"Sensor de Nivel 'SIM' detectado. Itens obrigatorios encontrados: {itens_encontrados_str}."}
        else:
            return {"regra": "Itens para Sensor de Nivel", "status": "FALHA", "detalhes": f"Sensor de Nivel 'SIM' detectado, mas os seguintes itens obrigatorios NAO foram encontrados: {', '.join(itens_faltando)}."}
    else:
        return {"regra": "Itens para Sensor de Nivel", "status": "OK", "detalhes": "Sensor de Nivel nao esta como 'SIM'. Regra nao aplicavel."}

def checar_regra_plaqueta_logotipo_atualizada(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    termo_novo = "plaqueta logotipo higra mining"
    termo_antigo = "plaqueta logotipo higra"
    if termo_novo in texto_normalizado:
        return { "regra": "Verificacao da Plaqueta Logotipo", "status": "OK", "detalhes": "Versao atualizada ('HIGRA MINING') foi encontrada." }
    elif termo_antigo in texto_normalizado:
        return { "regra": "Verificacao da Plaqueta Logotipo", "status": "FALHA", "detalhes": "AVISO: Versao antiga ('HIGRA') foi encontrada. Considerar atualizacao para 'HIGRA MINING'." }
    else:
        return { "regra": "Verificacao da Plaqueta Logotipo", "status": "FALHA", "detalhes": "Nenhuma versao da plaqueta de logotipo ('HIGRA' ou 'HIGRA MINING') foi encontrada." }

def checar_regra_mangueira_pvc(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    tamanho_cabo = _extrair_tamanho_cabo_flexivel(texto_normalizado)
    regra = "Mangueira PVC vs Diametro do Cabo"
    msg_extra_falha = "Dica: Checar e configurar a quantidade certa que deve ser 4 metros."
    if tamanho_cabo is None:
        return {"regra": regra, "status": "FALHA", "detalhes": "O item 'Cabo Flexivel com mm2' nao foi encontrado no documento."}
    mangueira_esperada = ""
    if tamanho_cabo < 50:
        mangueira_esperada = 'mangueira pvc trancada spt250 translucida 1/2"'
    elif 50 <= tamanho_cabo <= 95:
        mangueira_esperada = 'mangueira pvc trancada spt250 translucida 3/4"'
    else: # > 95
        mangueira_esperada = 'mangueira pvc trancada spt250 translucida 1"'
    if mangueira_esperada in texto_normalizado:
        return {"regra": regra, "status": "OK", "detalhes": f"Para o cabo de {tamanho_cabo}mm2, a mangueira correta ('{mangueira_esperada}') foi encontrada."}
    else:
        outras_mangueiras = ['mangueira pvc trancada spt250 translucida 1/2"', 'mangueira pvc trancada spt250 translucida 3/4"', 'mangueira pvc trancada spt250 translucida 1"']
        outra_encontrada = any(outra in texto_normalizado for outra in outras_mangueiras)
        if outra_encontrada:
            return {"regra": regra, "status": "FALHA", "detalhes": f"A polegada da mangueira esta errada. Para o cabo de {tamanho_cabo}mm2, a mangueira esperada era '{mangueira_esperada}'. {msg_extra_falha}"}
        else:
            return {"regra": regra, "status": "FALHA", "detalhes": f"Nenhuma mangueira PVC compativel foi encontrada para o cabo de {tamanho_cabo}mm2. A esperada era '{mangueira_esperada}'. {msg_extra_falha}"}

def checar_regra_tubo_termocontratil(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    tamanho_cabo = _extrair_tamanho_cabo_flexivel(texto_normalizado)
    regra = "Tubo Termocontratil vs Diametro do Cabo"
    msg_extra_falha = "Dica: Configurar com quantidade de 3,5 m."
    if tamanho_cabo is None:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel checar a regra pois o 'Cabo Flexivel' nao foi encontrado."}
    tubo_esperado = ""
    if tamanho_cabo < 70:
        tubo_esperado = 'tubo termocontratil 3/4"'
    elif 70 <= tamanho_cabo < 95:
        tubo_esperado = 'tubo termocontratil 1"'
    elif 95 <= tamanho_cabo <= 150:
        if 'tubo termoretratil 1.1/4"' in texto_normalizado or 'tubo termocontratil 1.1/4"' in texto_normalizado:
            return {"regra": regra, "status": "OK", "detalhes": f"Para o cabo de {tamanho_cabo}mm2, o tubo correto ('1.1/4\"') foi encontrado."}
        else:
            tubo_esperado = 'tubo termoretratil 1.1/4"'
    else: # > 150
        tubo_esperado = 'tubo termocontratil 1.1/2"'
    if tubo_esperado and tubo_esperado in texto_normalizado:
        return {"regra": regra, "status": "OK", "detalhes": f"Para o cabo de {tamanho_cabo}mm2, o tubo correto ('{tubo_esperado}') foi encontrado."}
    else:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Tubo termocontratil incorreto ou ausente. Para o cabo de {tamanho_cabo}mm2, o esperado era '{tubo_esperado}'. {msg_extra_falha}"}

def checar_regra_anel_o_cabo_flexivel(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    tamanho_cabo = _extrair_tamanho_cabo_flexivel(texto_normalizado)
    regra = "Anel O vs. Diametro do Cabo Flexivel"
    if tamanho_cabo is None:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel checar a regra pois o 'Cabo Flexivel' nao foi encontrado."}
    mapeamento_anel_o = {
        6: ["anel o nbr 2-110"], 10: ["anel o nbr 2-202"], 16: ["anel o nbr 2-202"],
        25: ["anel o nbr 2-204"], 35: ["anel o nbr 2-205"], 50: ["anel o nbr 2-206"],
        70: ["anel o nbr 2-207"], 95: ["anel o nbr 2-208", "anel o nbr 2-312"],
        120: ["anel o nbr 2-312"], 150: ["anel o nbr 2-315"], 185: ["anel o nbr 2-315"],
    }
    if tamanho_cabo not in mapeamento_anel_o:
        return {"regra": regra, "status": "OK", "detalhes": f"Cabo de {tamanho_cabo}mm2 encontrado, mas nao ha uma regra de Anel O especifica para este tamanho."}
    aneis_esperados = mapeamento_anel_o[tamanho_cabo]
    if any(anel in texto_normalizado for anel in aneis_esperados):
        return {"regra": regra, "status": "OK", "detalhes": f"Para o cabo de {tamanho_cabo}mm2, o Anel O correto ('{" ou ".join(aneis_esperados)}') foi encontrado."}
    else:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Anel O incorreto ou ausente. Para o cabo de {tamanho_cabo}mm2, o esperado era '{" ou ".join(aneis_esperados)}'."}

def checar_regra_anel_o_cabo_sensor(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    numero_eixo = _extrair_numero_eixo(texto_normalizado)
    regra = "Anel O vs. Cabo Sensor e Eixo"
    if numero_eixo is None:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel checar a regra pois o 'Eixo Bruto/Motriz' nao foi encontrado."}
    mapeamento_cabo_sensor = [
        {'cabo': 'cabo sensor shield 12x3', 'eixos': [315], 'anel': 'anel o nbr 2-312'},
        {'cabo': 'cabo sensor shield 12x3', 'eixos': [200], 'anel': 'anel o nbr 2-208'},
        {'cabo': 'cabo shield cabex 3x0',  'eixos': [160], 'anel': 'anel o nbr 2-108'},
        {'cabo': 'cabo shield cabex 3x0',  'eixos': [225, 315], 'anel': 'anel o nbr 2-202'},
        {'cabo': 'cabo sensor shield 8x3', 'eixos': [225], 'anel': 'anel o nbr 2-207'},
        {'cabo': 'cabo sensor shield 8x3', 'eixos': [315], 'anel': 'anel o nbr 2-311'},
    ]
    for regra_mapa in mapeamento_cabo_sensor:
        if regra_mapa['cabo'] in texto_normalizado and numero_eixo in regra_mapa['eixos']:
            anel_esperado = regra_mapa['anel']
            if anel_esperado in texto_normalizado:
                return {"regra": regra, "status": "OK", "detalhes": f"Para a combinacao de '{regra_mapa['cabo']}' e Eixo {numero_eixo}, o Anel O correto ('{anel_esperado}') foi encontrado."}
            else:
                return {"regra": regra, "status": "FALHA", "detalhes": f"Para a combinacao de '{regra_mapa['cabo']}' e Eixo {numero_eixo}, o Anel O esperado ('{anel_esperado}') NAO foi encontrado."}
    return {"regra": regra, "status": "OK", "detalhes": "Nenhuma combinacao de Cabo Sensor e Eixo aplicavel a esta regra foi encontrada."}

# --- NOVA REGRA ADICIONADA AQUI ---
def checar_regra_rotor_bomba(texto_completo_pdf):
    """Verifica se 'Rotor bomba' está presente e, se não, dá um aviso com os materiais da config."""
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    
    if "rotor bomba" in texto_normalizado:
        return {"regra": "Presenca do item Rotor Bomba", "status": "OK", "detalhes": "O item 'Rotor bomba' foi encontrado no documento."}
    else:
        # Se não encontrou, vamos extrair os materiais da config para a mensagem de erro
        material_rotor = "Nao identificado"
        material_difusor = "Nao identificado"
        
        match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
        if match_config:
            string_config = match_config.group(1)
            valores = string_config.split('#')
            # Rotor é o 10º (índice 9), Difusor é o 11º (índice 10)
            if len(valores) > 10:
                material_rotor = valores[9]
                material_difusor = valores[10]

        detalhes_falha = f"Item 'Rotor bomba' nao encontrado. Checar cadastro do rotor e do difusor para os materiais (Rotor: {material_rotor}, Difusor: {material_difusor})"
        return {"regra": "Presenca do item Rotor Bomba", "status": "FALHA", "detalhes": detalhes_falha}

# --- SUBSTITUA A FUNÇÃO ANTIGA DO SELO MECÂNICO POR ESTA VERSÃO ATUALIZADA ---
def checar_regra_selo_mecanico(texto_completo_pdf):
    """
    Verifica o material do Selo Mecanico com base no material do Rotor.
    VERSÃO ATUALIZADA: Procura o material na linha do selo e na linha seguinte.
    """
    regra = "Material do Selo Mecanico vs. Rotor"
    material_rotor = _extrair_material_rotor(texto_completo_pdf)
    
    if not material_rotor:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel identificar o material do rotor na config para validar a regra."}

    # Define o material esperado para o selo
    gatilhos_especiais = ("ROT INOX316", "ROT AISI316", "ROT CD4MCUN")
    material_selo_esperado = "inox316" if material_rotor.startswith(gatilhos_especiais) else "inox304"

    # Encontra todas as linhas que contêm "selo mecanico"
    todas_as_linhas = texto_completo_pdf.splitlines()
    indices_selos_encontrados = [
        i for i, linha in enumerate(todas_as_linhas) 
        if "selo mecanico" in _normalizar_texto_completo(linha)
    ]

    if not indices_selos_encontrados:
        return {"regra": regra, "status": "FALHA", "detalhes": "Nenhum item 'Selo Mecanico' foi encontrado no documento."}

    # Verifica cada selo encontrado
    for i in indices_selos_encontrados:
        # Cria um "bloco de busca" com a linha atual e a próxima
        linha_atual = _normalizar_texto_completo(todas_as_linhas[i])
        linha_seguinte = ""
        if (i + 1) < len(todas_as_linhas):
            linha_seguinte = _normalizar_texto_completo(todas_as_linhas[i+1])
        
        bloco_de_busca = linha_atual + " " + linha_seguinte

        if material_selo_esperado not in bloco_de_busca:
            return {"regra": regra, "status": "FALHA", "detalhes": f"Material do Rotor e '{material_rotor}'. O Selo Mecanico (linha {i+1} do PDF) deveria conter '{material_selo_esperado}', mas nao foi encontrado nas linhas adjacentes."}

    return {"regra": regra, "status": "OK", "detalhes": f"Material do Rotor e '{material_rotor}'. Todos os {len(indices_selos_encontrados)} selo(s) mecanico(s) estao com o material correto ('{material_selo_esperado}')."}

def checar_regra_anel_desgaste(texto_completo_pdf):
    """Para rotores especiais, verifica se o Anel de Desgaste contém INOX420."""
    regra = "Material do Anel de Desgaste vs. Rotor"
    material_rotor = _extrair_material_rotor(texto_completo_pdf)

    if not material_rotor:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel identificar o material do rotor na config para validar a regra."}

    gatilhos_especiais = ("ROT INOX316", "ROT AISI316", "ROT CD4MCUN")
    if not material_rotor.startswith(gatilhos_especiais):
        return {"regra": regra, "status": "OK", "detalhes": f"Rotor nao e de material especial. Regra nao aplicavel."}

    # Se o rotor é especial, a regra se aplica
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    linhas_com_anel = [linha for linha in texto_completo_pdf.splitlines() if "anel desgaste" in _normalizar_texto_completo(linha)]

    if not linhas_com_anel:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Rotor e de material especial ({material_rotor}), mas nenhum 'Anel Desgaste' foi encontrado."}

    for i, linha in enumerate(linhas_com_anel):
        if "inox420" not in _normalizar_texto_completo(linha):
            return {"regra": regra, "status": "FALHA", "detalhes": f"Rotor e de material especial ({material_rotor}). O 'Anel Desgaste' na linha {i+1} deveria conter 'inox420', mas nao foi encontrado."}

    return {"regra": regra, "status": "OK", "detalhes": f"Rotor e de material especial ({material_rotor}). Todos os {len(linhas_com_anel)} anel(eis) de desgaste estao com o material correto ('inox420')."}



def checar_regra_componentes_especiais_selo(texto_completo_pdf):
    """
    Para rotores especiais (316/CD4MCUN), verifica se o Protetor do Selo,
    a Placa de Travamento e a Caixa de Selo contêm 'inox316'.
    """
    regra = "Materiais dos Componentes do Selo vs. Rotor"
    material_rotor = _extrair_material_rotor(texto_completo_pdf)

    if not material_rotor:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel identificar o material do rotor na config para validar a regra."}

    gatilhos_especiais = ("ROT INOX316", "ROT AISI316", "ROT CD4MCUN")
    if not material_rotor.startswith(gatilhos_especiais):
        return {"regra": regra, "status": "OK", "detalhes": f"Rotor ({material_rotor}) nao e de material especial. Regra nao aplicavel."}

    # Se o rotor é especial, a regra se aplica.
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    erros = []

    # --- A MUDANÇA ESTÁ AQUI: Adicionando 'caixa selo' à lista de termos ---
    itens_a_checar = [
        {'nome': 'Protetor do Selo', 'termos': ['protetor do selo', 'protetor selo'], 'material_esperado': 'inox316'},
        {'nome': 'Placa de Travamento', 'termos': ['placa de travamento', 'placa travamento'], 'material_esperado': 'inox316'},
        {'nome': 'Caixa de Selo', 'termos': ['caixa de selo', 'caixa selo'], 'material_esperado': 'inox316'}
    ]

    for item in itens_a_checar:
        # Encontra todas as linhas que contêm o item
        linhas_encontradas = [
            linha for linha in texto_completo_pdf.splitlines()
            if any(termo in _normalizar_texto_completo(linha) for termo in item['termos'])
        ]

        if not linhas_encontradas:
            erros.append(f"Item obrigatorio '{item['nome']}' nao foi encontrado.")
            continue # Pula para o próximo item da lista

        # Se encontrou o item, verifica o material em cada linha
        for i, linha in enumerate(linhas_encontradas):
            if item['material_esperado'] not in _normalizar_texto_completo(linha):
                erros.append(f"O item '{item['nome']}' (encontrado na linha {i+1} do PDF) nao contem o material esperado '{item['material_esperado']}'.")

    # Reporta o resultado final
    if not erros:
        return {"regra": regra, "status": "OK", "detalhes": f"Rotor e de material especial. Todos os componentes do selo (Protetor, Placa de Travamento, Caixa de Selo) estao com o material correto ('inox316')."}
    else:
        detalhes_falha = f"Rotor e de material especial ({material_rotor}), mas foram encontrados os seguintes problemas: {'; '.join(erros)}"
        return {"regra": regra, "status": "FALHA", "detalhes": detalhes_falha}

# --- SUBSTITUA A FUNÇÃO ANTIGA DE POTÊNCIA VS CABO POR ESTA VERSÃO ATUALIZADA ---
def checar_regra_potencia_cabo_flexivel(texto_completo_pdf):
    """Para potências entre 300CV e 400CV, verifica se o cabo flexível é de 95mm²."""
    potencia = _extrair_potencia_config(texto_completo_pdf)
    regra = "Cabo Flexivel vs. Potencia"

    if potencia is None:
        return {"regra": regra, "status": "FALHA", "detalhes": "Nao foi possivel extrair a potencia da string de configuracao."}

    # A regra só se aplica para potências entre 300 e 400 (inclusivo)
    if not (300 <= potencia <= 400):
        return {"regra": regra, "status": "OK", "detalhes": f"Potencia ({potencia}CV) fora da faixa de 300-400CV. Regra nao aplicavel."}

    # --- A MUDANÇA COMEÇA AQUI: Adicionando a mensagem de dica ---
    msg_dica_falha = "Dica: Se alterar o cabo, lembrar de alterar tambem o prensa-cabo e o tampao dos fios."
    
    # Se a potência está na faixa, a verificação é necessária
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    
    linhas_com_cabo = [
        linha for linha in texto_completo_pdf.splitlines() 
        if "cabo flexivel" in _normalizar_texto_completo(linha)
    ]

    if not linhas_com_cabo:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Potencia e de {potencia}CV, mas nenhum item 'Cabo Flexivel' foi encontrado. {msg_dica_falha}"}

    # Verifica se alguma das linhas encontradas tem o diâmetro correto
    diametro_correto_encontrado = False
    for linha in linhas_com_cabo:
        if re.search(r"95\s*mm[2²]", _normalizar_texto_completo(linha)):
            diametro_correto_encontrado = True
            break

    if diametro_correto_encontrado:
        return {"regra": regra, "status": "OK", "detalhes": f"Potencia e de {potencia}CV. O 'Cabo Flexivel' com o diametro correto (95mm²) foi encontrado."}
    else:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Potencia e de {potencia}CV, mas o 'Cabo Flexivel' com diametro de 95mm² NAO foi encontrado. {msg_dica_falha}"}
        
# Criando as regras de fábrica
checar_regra_plaqueta_sentido_giro = _criar_checador_presenca_obrigatoria("Presenca de Plaqueta Sentido de Giro", "plaqueta sentido de giro")
checar_regra_plaqueta_identifica = _criar_checador_presenca_obrigatoria("Presenca de Plaqueta de Identificacao", "plaqueta identifica")
checar_regra_plaqueta_guia_geral = _criar_checador_contagem_obrigatoria("Presenca de Plaqueta Guia", "plaqueta guia")

def checar_regra_tubo_fluxo_rosca(texto_completo_pdf):
    """Verifica se 'tubo de fluxo' e 'rosca' aparecem juntos."""
    regra = "Verificacao Tubo de Fluxo com Rosca"
    todas_as_linhas = texto_completo_pdf.splitlines()
    
    indices_tubo_fluxo = [
        i for i, linha in enumerate(todas_as_linhas) 
        if "tubo de fluxo" in _normalizar_texto_completo(linha)
    ]

    if not indices_tubo_fluxo:
        return {"regra": regra, "status": "FALHA", "detalhes": "O item 'Tubo de Fluxo' nao foi encontrado no documento."}

    for i in indices_tubo_fluxo:
        linha_atual_norm = _normalizar_texto_completo(todas_as_linhas[i])
        
        # Checa a linha atual
        if "rosca" in linha_atual_norm:
            continue 

        # Checa a linha seguinte, se ela existir
        if (i + 1) < len(todas_as_linhas):
            linha_seguinte_norm = _normalizar_texto_completo(todas_as_linhas[i+1])
            if "rosca" in linha_seguinte_norm:
                continue 

        # Se chegou aqui, 'rosca' não foi encontrada perto do 'tubo de fluxo'
        return {"regra": regra, "status": "FALHA", "detalhes": f"O item 'Tubo de Fluxo' foi encontrado (linha ~{i+1} do PDF), mas a palavra 'rosca' nao foi encontrada na mesma linha ou na linha seguinte."}

    # Se o loop terminar, todas as ocorrências estavam corretas
    return {"regra": regra, "status": "OK", "detalhes": f"Encontrado(s) {len(indices_tubo_fluxo)} item(ns) 'Tubo de Fluxo' e todos possuem a especificacao 'rosca' proxima."}


def checar_regra_prensa_cabo_tampa_fio(texto_completo_pdf):
    """Verifica a presença obrigatória de 'prensa-cabo' e 'tampa dos fio'."""
    regra = "Presenca de Prensa-Cabo e Tampa dos Fios"
    texto_normalizado_doc = _normalizar_texto_completo(texto_completo_pdf)
    
    itens_obrigatorios = ["prensa-cabo", "tampa dos fio"]
    itens_faltando = []

    for item in itens_obrigatorios:
        if item not in texto_normalizado_doc:
            itens_faltando.append(item)

    if not itens_faltando:
        return {"regra": regra, "status": "OK", "detalhes": "Os itens obrigatorios 'prensa-cabo' e 'tampa dos fio' foram encontrados."}
    else:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Nao foram encontrados os seguintes itens obrigatorios: {', '.join(itens_faltando)}."}

# -------------------------------------------------------------------
# AQUI FICA O ORQUESTRADOR PRINCIPAL DO CHECKLIST
# -------------------------------------------------------------------
def executar_checklist_completo(texto_pdf):
    regras_a_checar = [
        checar_regra_eixo_bruto,
        checar_regra_exportacao,
        checar_regra_sensores_protetor,
        checar_regra_sensores_cabo_shield,
        _criar_checador_presenca_obrigatoria("Presenca de Supressor Trifasico", "supressor trifasico"),
        checar_regra_plaqueta_sentido_giro,
        checar_regra_plaqueta_identifica,
        checar_regra_plaqueta_logotipo_atualizada,
        checar_regra_plaqueta_guia_geral,
        checar_regra_pistao_agua_limpa,
        checar_regra_controlador_novus,
        checar_regra_fieldlogger,
        checar_regra_chassi_modelos,
        checar_regra_bujao_modificada,
        checar_regra_tubo_termocontratil_potencia,
        checar_regra_contagem_tubo_termo,
        checar_regra_sensor_nivel_itens,
        checar_regra_mangueira_pvc,
        checar_regra_tubo_termocontratil,
        checar_regra_anel_o_cabo_flexivel,
        checar_regra_anel_o_cabo_sensor,
        checar_regra_rotor_bomba,
        # Adicionando as novas regras de hoje
        checar_regra_selo_mecanico,
        checar_regra_anel_desgaste,
        checar_regra_componentes_especiais_selo,
        checar_regra_potencia_cabo_flexivel,
        checar_regra_tubo_fluxo_rosca,
        checar_regra_prensa_cabo_tampa_fio,
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
st.title("✅ Verificador Automático de Relatório de custos em PDF")
st.write("Faça o upload do arquivo PDF para iniciar a verificação.")
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
                texto_normalizado_debug = _normalizar_texto_completo(texto_completo)
                st.text_area("Conteúdo:", texto_normalizado_debug, height=250)

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













