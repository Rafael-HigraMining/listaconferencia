import streamlit as st
import fitz  # PyMuPDF
import re
import io
import unicodedata

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

# --- SUBSTITUA A FUNÇÃO AJUDANTE ANTIGA POR ESTA VERSÃO ATUALIZADA ---
def _extrair_tamanho_cabo_flexivel(texto_normalizado):
    """
    Busca pelo cabo flexível no texto e extrai o seu diâmetro.
    VERSÃO ATUALIZADA: Aceita tanto 'mm2' quanto 'mm²'.
    """
    # A mudança está no final da regex: [2²] aceita o caractere '2' OU o caractere '²'.
    match = re.search(r"cabo flexivel.*?(\d+)\s*mm[2²]", texto_normalizado)
    if match:
        return int(match.group(1))
    return None

def _extrair_numero_eixo(texto_normalizado):
    match = re.search(r"(eixo bruto|eixo motriz).*?(\d+)[sl]", texto_normalizado)
    if match:
        return int(match.group(2))
    return None

# --- FUNÇÃO DO EIXO ATUALIZADA PARA USAR O NOVO AJUDANTE ---
def checar_regra_eixo_bruto(texto_completo_pdf):
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    numero_eixo = _extrair_numero_eixo(texto_normalizado)

    if not numero_eixo: 
        return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": "A expressao 'eixo bruto' ou 'eixo motriz' seguida de um numero e S/L nao foi encontrada." }
    
    if numero_eixo >= 225:
        tem_ranhurado = "grafite ranhurado" in texto_normalizado
        tem_liso = "grafite liso" in texto_normalizado
        if tem_ranhurado and tem_liso: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "OK", "detalhes": f"Eixo ({numero_eixo}) >= 225. 'Grafite ranhurado' e 'Grafite liso' encontrados como esperado." }
        else:
            erros = []
            if not tem_ranhurado: erros.append("'grafite ranhurado' nao foi encontrado")
            if not tem_liso: erros.append("'grafite liso' nao foi encontrado")
            return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) >= 225. Erro: {', '.join(erros)}." }
    else:
        tem_liso = "grafite liso" in texto_normalizado
        if not tem_liso: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "OK", "detalhes": f"Eixo ({numero_eixo}) < 225. 'Grafite liso' nao foi encontrado, como esperado." }
        else: return { "regra": "Eixo Bruto/Motriz vs Grafites", "status": "FALHA", "detalhes": f"Eixo ({numero_eixo}) < 225. Erro: 'Grafite liso' foi encontrado, o que nao e permitido." }

# (O restante das funções antigas continua aqui, sem alterações...)
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
    inox_check_requerido = False
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if match_config:
        string_config = match_config.group(1)
        valores = string_config.split('#')
        if len(valores) > 9 and valores[9].upper() == "ROT INOX316": inox_check_requerido = True
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
                return { "regra": "Verificacao de Bujao", "status": "FALHA", "detalhes": f"Rotor e INOX316, mas a linha {linha_info['num_linha']} contem '{termo_bujao}' SEM a especificacao 'inox316'." }
        return { "regra": "Verificacao de Bujao", "status": "OK", "detalhes": f"Rotor e INOX316. Encontrado(s) {len(linhas_com_bujao)} bujao(oes) e todos contem 'inox316' como esperado." }
    else:
        return { "regra": "Verificacao de Bujao", "status": "OK", "detalhes": f"Rotor nao e INOX316. Encontrado(s) {len(linhas_com_bujao)} bujao(oes) no documento." }

def checar_regra_tubo_termocontratil_potencia(texto_completo_pdf):
    match_config = re.search(r"Config\.+:\s*(.*)", texto_completo_pdf, re.IGNORECASE | re.DOTALL)
    if not match_config: return {"regra": "Tubo Termocontratil vs Potencia", "status": "FALHA", "detalhes": "A linha 'Config...........:' nao foi encontrada."}
    string_config = match_config.group(1)
    valores = string_config.split('#')
    if len(valores) < 6:
        return {"regra": "Tubo Termocontratil vs Potencia", "status": "FALHA", "detalhes": "Nao foi possivel encontrar o campo de potencia na string de configuracao."}
    potencia_str = valores[5]
    match_potencia = re.search(r'(\d+)', potencia_str)
    if not match_potencia:
        return {"regra": "Tubo Termocontratil vs Potencia", "status": "FALHA", "detalhes": f"Nao foi possivel extrair um valor numerico do campo de potencia ('{potencia_str}')."}
    potencia = int(match_potencia.group(1))
    if potencia > 75:
        texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
        termo_proibido = 'tubo termocontratil 1/2"'
        if termo_proibido in texto_normalizado:
            return {"regra": "Tubo Termocontratil vs Potencia", "status": "FALHA", "detalhes": f"Potencia ({potencia}CV) > 75CV e o termo proibido '{termo_proibido}' foi encontrado."}
        else:
            return {"regra": "Tubo Termocontratil vs Potencia", "status": "OK", "detalhes": f"Potencia ({potencia}CV) > 75CV e o termo proibido nao foi encontrado, como esperado."}
    else: # Potencia <= 75
        return {"regra": "Tubo Termocontratil vs Potencia", "status": "OK", "detalhes": f"Potencia ({potencia}CV) <= 75CV. A regra de restricao nao se aplica."}

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
    elif 70 <= tamanho_cabo <= 120:
        tubo_esperado = 'tubo termocontratil 1"'
    elif tamanho_cabo == 150:
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

# --- NOVAS REGRAS DE HOJE ADICIONADAS AQUI ---
def checar_regra_anel_o_cabo_flexivel(texto_completo_pdf):
    """Verifica se o Anel O correto está presente, com base no diâmetro específico do cabo."""
    texto_normalizado = _normalizar_texto_completo(texto_completo_pdf)
    tamanho_cabo = _extrair_tamanho_cabo_flexivel(texto_normalizado)
    
    regra = "Anel O vs. Diametro do Cabo Flexivel"

    if tamanho_cabo is None:
        return {"regra": regra, "status": "OK", "detalhes": "Nao foi possivel checar a regra pois o 'Cabo Flexivel' nao foi encontrado."}

    mapeamento_anel_o = {
        6: ["anel o nbr 2-110"],
        10: ["anel o nbr 2-202"],
        16: ["anel o nbr 2-202"],
        25: ["anel o nbr 2-204"],
        35: ["anel o nbr 2-205"],
        50: ["anel o nbr 2-206"],
        70: ["anel o nbr 2-207"],
        95: ["anel o nbr 2-208", "anel o nbr 2-312"],
        120: ["anel o nbr 2-312"],
        150: ["anel o nbr 2-315"],
        185: ["anel o nbr 2-315"],
    }

    if tamanho_cabo not in mapeamento_anel_o:
        return {"regra": regra, "status": "OK", "detalhes": f"Cabo de {tamanho_cabo}mm2 encontrado, mas nao ha uma regra de Anel O especifica para este tamanho."}

    aneis_esperados = mapeamento_anel_o[tamanho_cabo]
    
    # Verifica se qualquer um dos anéis esperados (para o caso do 'OU') está no texto
    if any(anel in texto_normalizado for anel in aneis_esperados):
        return {"regra": regra, "status": "OK", "detalhes": f"Para o cabo de {tamanho_cabo}mm2, o Anel O correto ('{" ou ".join(aneis_esperados)}') foi encontrado."}
    else:
        return {"regra": regra, "status": "FALHA", "detalhes": f"Anel O incorreto ou ausente. Para o cabo de {tamanho_cabo}mm2, o esperado era '{" ou ".join(aneis_esperados)}'."}

def checar_regra_anel_o_cabo_sensor(texto_completo_pdf):
    """Verifica o Anel O com base na combinação do tipo de Cabo Sensor e o número do Eixo."""
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

    # Itera sobre o mapa de regras para encontrar uma que se aplique a este PDF
    for regra_mapa in mapeamento_cabo_sensor:
        if regra_mapa['cabo'] in texto_normalizado and numero_eixo in regra_mapa['eixos']:
            # Encontramos a condição que se aplica, agora verificamos a consequência
            anel_esperado = regra_mapa['anel']
            if anel_esperado in texto_normalizado:
                return {"regra": regra, "status": "OK", "detalhes": f"Para a combinacao de '{regra_mapa['cabo']}' e Eixo {numero_eixo}, o Anel O correto ('{anel_esperado}') foi encontrado."}
            else:
                return {"regra": regra, "status": "FALHA", "detalhes": f"Para a combinacao de '{regra_mapa['cabo']}' e Eixo {numero_eixo}, o Anel O esperado ('{anel_esperado}') NAO foi encontrado."}

    # Se o loop terminar sem encontrar nenhuma combinação aplicável
    return {"regra": regra, "status": "OK", "detalhes": "Nenhuma combinacao de Cabo Sensor e Eixo aplicavel a esta regra foi encontrada."}


# Criando as regras de fábrica
checar_regra_plaqueta_sentido_giro = _criar_checador_presenca_obrigatoria("Presenca de Plaqueta Sentido de Giro", "plaqueta sentido de giro")
checar_regra_plaqueta_identifica = _criar_checador_presenca_obrigatoria("Presenca de Plaqueta de Identificacao", "plaqueta identifica")
checar_regra_plaqueta_guia_geral = _criar_checador_contagem_obrigatoria("Presenca de Plaqueta Guia", "plaqueta guia")

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
        checar_regra_anel_o_cabo_flexivel, # <-- NOVA REGRA ADICIONADA
        checar_regra_anel_o_cabo_sensor,   # <-- NOVA REGRA ADICIONADA
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

