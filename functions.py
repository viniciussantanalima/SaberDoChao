# functions.py

import flet as ft
from typing import Optional, List, cast
import csv
from datetime import datetime
import os
import tempfile
import re  # <--- ADICIONE ESTA LINHA AQUI

def obter_pasta_segura():
    # Use o diretório interno do app sempre que disponível.
    pasta = os.environ.get("FLET_APP_STORAGE_DATA")
    if pasta:
        pasta = os.path.abspath(pasta)
    else:
        android_env = "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ
        if android_env:
            pasta = os.environ.get("HOME") or os.environ.get("ANDROID_DATA") or os.getcwd() or tempfile.gettempdir()
            pasta = os.path.abspath(pasta)
            pasta = os.path.join(pasta, ".saberdochao")
        else:
            pasta = os.path.join(os.path.expanduser("~"), ".saberdochao")

    if not pasta:
        pasta = tempfile.gettempdir()

    try:
        os.makedirs(pasta, exist_ok=True)
    except PermissionError:
        pasta = os.path.join(tempfile.gettempdir(), ".saberdochao")
        os.makedirs(pasta, exist_ok=True)
    except Exception:
        pasta = tempfile.gettempdir()

    return pasta

def obter_caminho_csv():
    return os.path.join(obter_pasta_segura(), "plantas.csv")

def reordenar_canteiros(
    e: ft.OnReorderEvent,
    coluna_canteiros: ft.ReorderableListView,
    page: ft.Page,
) -> None:
    if e.old_index is None or e.new_index is None:
        return
    item = coluna_canteiros.controls.pop(e.old_index)
    coluna_canteiros.controls.insert(e.new_index, item)
    page.update()

def criar_canteiro(
    page: ft.Page,
    coluna_canteiros: ft.ReorderableListView,
    nome_inicial: str,
    quantidade_plantas: int = 0,
    plantas_iniciais: Optional[list] = None,
) -> ft.Card:
    
    dados_do_canteiro = {
        "nome": nome_inicial,
        "plantas": []
    }

    caminho_csv = obter_caminho_csv()

    # Garante que o CSV existe antes de ler plantas_db_local
    if not os.path.exists(caminho_csv) or os.path.getsize(caminho_csv) < 200:
        try:
            from dados_iniciais import CSV_FABRICA
            os.makedirs(os.path.dirname(caminho_csv), exist_ok=True)
            with open(caminho_csv, "w", encoding="utf-8") as f:
                f.write(CSV_FABRICA.strip() + "\n")
        except Exception as e:
            print(f"[criar_canteiro] Erro ao criar CSV: {e}")

    titulo_texto = ft.Text(
        nome_inicial,
        weight=ft.FontWeight.BOLD,
        size=16,
        color=ft.Colors.BLACK
    )

    titulo_input = ft.TextField(
        value=nome_inicial,
        text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
        dense=True,
        content_padding=0,
        border=ft.InputBorder.UNDERLINE,
        border_color='#1BB241',
        visible=False,
        expand=True
    )

    def habilitar_edicao(e):
        titulo_interativo.visible = False
        titulo_input.visible = True
        titulo_input.focus()
        page.update()

    def salvar_edicao(e):
        if titulo_input.value.strip() != "":
            titulo_texto.value = titulo_input.value
            dados_do_canteiro["nome"] = titulo_input.value
        titulo_interativo.visible = True
        titulo_input.visible = False
        page.update()

    titulo_input.on_submit = salvar_edicao
    titulo_input.on_blur = salvar_edicao

    titulo_interativo = ft.GestureDetector(
        content=titulo_texto,
        on_double_tap=habilitar_edicao,
    )

    contador_plantas = ft.Text("", size=12, color=ft.Colors.GREY_600)

    lista_plantas = ft.Column(expand=True, controls=cast(List[ft.Control], []), spacing=6)

    def atualizar_contagem():
        total = len(lista_plantas.controls)
        contador_plantas.value = f"{total} Planta{'s' if total != 1 else ''} registrad{'as' if total != 1 else 'a'}"

    def criar_planta_visual(dados_planta_dict: dict, colheita_info, freq_rega: int) -> ft.Container:

        caminho_csv = obter_caminho_csv()

        nome = dados_planta_dict.get("nome", "Desconhecida")
        data_plantio_str = dados_planta_dict.get("data_plantio", datetime.today().strftime('%d/%m/%Y'))
        
        cor_fundo = ft.Colors.GREEN_100
        cor_texto = ft.Colors.GREEN_900
        status_texto = ""
        precisa_regar = False

        def interpretar_sazonalidade(texto):
            texto = str(texto).lower()
            # Mapeia as variações e erros comuns para o número do mês
            mapa_meses = {
                1: ['jan'], 2: ['fev'], 3: ['mar'], 4: ['abr', 'abriu'], 
                5: ['mai'], 6: ['jun'], 7: ['jul'], 8: ['ago'], 
                9: ['set'], 10: ['out', 'otu'], 11: ['nov'], 12: ['dez']
            }
            
            meses_encontrados = []
            for num_mes, variaveis in mapa_meses.items():
                for var in variaveis:
                    # Busca a variação como início de palavra, ignorando o resto
                    para_buscar = r'\b' + var + r'[a-z]*\b'
                    for match in re.finditer(para_buscar, texto):
                        meses_encontrados.append((match.start(), num_mes))
                        
            if meses_encontrados:
                # Ordena pela posição onde a palavra apareceu na frase (quem vem primeiro)
                meses_encontrados.sort() 
                inicio = meses_encontrados[0][1]
                fim = meses_encontrados[-1][1]
                return (inicio, fim)
            return None

        # Decide se é Cronológico (Dias) ou Sazonal (Meses)
        dias_colheita = None
        periodo_sazonal = None
        
        texto_colheita = str(colheita_info).strip()
        if texto_colheita.isdigit():
            dias_colheita = int(texto_colheita)
        else:
            periodo_sazonal = interpretar_sazonalidade(texto_colheita)
            # Se o utilizador escreveu algo ilegível e não é número, assume 90 dias
            if not periodo_sazonal:
                dias_colheita = 90

        try:
            data_plantio = datetime.strptime(data_plantio_str, "%d/%m/%Y")
            dias_passados = (datetime.today() - data_plantio).days
            
            # Evita divisão por zero se freq_rega for 0
            precisa_regar = (dias_passados >= 0) and (freq_rega > 0 and dias_passados % freq_rega == 0)

            # LÓGICA DE ÁRVORES E SAZONALIDADE
            if periodo_sazonal:
                inicio, fim = periodo_sazonal
                mes_atual = datetime.today().month
                
                # Verifica se está no período (suporta virada de ano, ex: Nov a Fev)
                if inicio <= fim:
                    dentro_da_epoca = inicio <= mes_atual <= fim
                else:
                    dentro_da_epoca = mes_atual >= inicio or mes_atual <= fim

                if dentro_da_epoca:
                    cor_fundo = ft.Colors.GREEN_100
                    status_texto = "Período Ativo (Época de Frutos/Colheita)"
                else:
                    cor_fundo = ft.Colors.GREY_300
                    cor_texto = ft.Colors.GREY_800
                    status_texto = "Fora de época de produção"
                    
            # LÓGICA DE HORTALIÇAS (DIAS)
            elif dias_colheita is not None:
                dias_restantes = dias_colheita - dias_passados
                
                if dias_restantes <= 0:
                    cor_fundo = ft.Colors.RED_100
                    cor_texto = ft.Colors.RED_900
                    status_texto = "Pronta para colher!"
                elif dias_restantes <= 7:
                    cor_fundo = ft.Colors.YELLOW_100
                    cor_texto = ft.Colors.ORANGE_900
                    status_texto = f"Colheita em {dias_restantes} dias!"
                else:
                    status_texto = f"Crescendo (Faltam {dias_restantes} dias)"
                    
        except ValueError:
            cor_fundo = ft.Colors.GREY_300
            cor_texto = ft.Colors.GREY_800
            status_texto = "Data inválida"
            precisa_regar = False

        botao_regar = ft.IconButton(
            icon=ft.Icons.WATER_DROP,
            icon_color=ft.Colors.BLUE if precisa_regar else ft.Colors.GREY_400,
            tooltip="Precisa de água hoje!" if precisa_regar else f"Regar a cada {freq_rega} dias",
        )

        botao_remover = ft.IconButton(
            icon=ft.Icons.DELETE,
            icon_color=ft.Colors.GREY_700,
            tooltip="Remover Planta",
        )

        planta = ft.Container(
            bgcolor=cor_fundo,
            padding=ft.Padding.only(left=10, top=8, bottom=8, right=0),
            border_radius=6,
            content=ft.Row(
                controls=cast(List[ft.Control], [
                    ft.Column([
                        ft.Text(nome, size=14, weight=ft.FontWeight.W_600, color=cor_texto),
                        ft.Text(f"Plantio: {data_plantio_str} | {status_texto}", size=11, color=cor_texto)
                    ], spacing=2, expand=True),
                    
                    ft.Row([botao_regar, botao_remover], spacing=0) 
                ]),
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
        )

        def regar_planta(e):
            botao_regar.icon_color = ft.Colors.GREY_400
            botao_regar.tooltip = "Regada com sucesso!"
            dados_planta_dict["ultima_rega"] = datetime.today().strftime('%d/%m/%Y')
            page.update()
            
        botao_regar.on_click = regar_planta

        def on_remover(e):
            if planta in lista_plantas.controls:
                lista_plantas.controls.remove(planta)
                if dados_planta_dict in dados_do_canteiro["plantas"]:
                    dados_do_canteiro["plantas"].remove(dados_planta_dict)
                atualizar_contagem()
                page.update()

        botao_remover.on_click = on_remover
        return planta

    plantas_db_local = {}
    try:
        with open(caminho_csv, mode='r', encoding='utf-8') as arquivo:
            for linha in csv.DictReader(arquivo, delimiter=';'):
                nome_csv = linha.get('Nome da Planta')
                if nome_csv and nome_csv.strip() != "":
                    dias = str(linha.get('Tempo de Colheita (Em Dias)', '90')).strip()
                    rega = str(linha.get('Frequência de Rega (Em Dias)', '1')).strip()
                    
                    valor_sol = linha.get('Quantidade de Sol')
                    if valor_sol is None:
                        sol_valor = 'Pleno Sol'
                    else:
                        sol_valor = str(valor_sol).strip()
                    
                    plantas_db_local[nome_csv.strip()] = {
                        'colheita': dias,
                        'rega': int(rega) if rega.isdigit() else 1,
                        'sol': sol_valor
                    }
    except FileNotFoundError:
        pass

    if plantas_iniciais is None:
        plantas_iniciais = []
        
    for p_item in plantas_iniciais:
        if isinstance(p_item, str):
            dict_inicial = {"nome": p_item, "data_plantio": datetime.today().strftime('%d/%m/%Y'), "ultima_rega": "Ainda não regada"}
        else:
            dict_inicial = p_item
            
        dados_csv = plantas_db_local.get(dict_inicial.get("nome"), {'colheita': 90, 'rega': 1})
        dados_do_canteiro["plantas"].append(dict_inicial)
        lista_plantas.controls.append(criar_planta_visual(dict_inicial, dados_csv['colheita'], dados_csv['rega']))

    def abrir_dialogo_plantio(e):

        caminho_csv = obter_caminho_csv()

        # Garante que o CSV existe antes de listar plantas disponíveis
        if not os.path.exists(caminho_csv) or os.path.getsize(caminho_csv) < 200:
            try:
                from dados_iniciais import CSV_FABRICA
                os.makedirs(os.path.dirname(caminho_csv), exist_ok=True)
                with open(caminho_csv, "w", encoding="utf-8") as f:
                    f.write(CSV_FABRICA.strip() + "\n")
            except Exception as e:
                print(f"[abrir_dialogo_plantio] Erro ao criar CSV: {e}")

        plantas_db = {}
        opcoes = []
        try:
            with open(caminho_csv, mode='r', encoding='utf-8') as arquivo:
                for linha in csv.DictReader(arquivo, delimiter=';'):
                    nome = linha.get('Nome da Planta')
                    if nome and nome.strip() != "":
                        nome = nome.strip()
                        dias = str(linha.get('Tempo de Colheita (Em Dias)', '90')).strip()
                        rega = str(linha.get('Frequência de Rega (Em Dias)', '1')).strip()
                        pops = [str(linha.get(f'Nome Popular {i}', '')).strip() for i in range(1, 4)]
                        pops = [p for p in pops if p]
                        plantas_db[nome] = {
                            'colheita': int(dias) if dias.isdigit() else 90,
                            'rega': int(rega) if rega.isdigit() else 1,
                            'populares': pops,
                        }
                        opcoes.append(ft.dropdown.Option(nome))
        except FileNotFoundError:
            pass

        if not opcoes:
            opcoes.append(ft.dropdown.Option("Nenhuma planta registrada"))

        planta_selecionada = {"nome": None}

        campo_pesquisa_planta = ft.TextField(
            label="Pesquisar planta...",
            dense=True,
            autofocus=True,
        )

        texto_selecionada = ft.Text("", size=13, color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)

        container_resultados = ft.Container(
            height=0,
            content=ft.ListView(spacing=4),
        )

        def selecionar(nome):
            planta_selecionada["nome"] = nome
            texto_selecionada.value = f"✓ {nome}"
            texto_selecionada.color = ft.Colors.GREEN_700
            container_resultados.content.controls.clear()
            container_resultados.height = 0
            campo_pesquisa_planta.value = ""
            page.update()

        def filtrar(ev):
            termo = campo_pesquisa_planta.value.lower().strip() if campo_pesquisa_planta.value else ""
            container_resultados.content.controls.clear()
            if not termo:
                container_resultados.height = 0
                page.update()
                return
            for nome, dados in plantas_db.items():
                textos = [nome.lower()] + [p.lower() for p in dados['populares']]
                if any(termo in t for t in textos):
                    def fazer_clique(n):
                        return lambda ev: selecionar(n)
                    container_resultados.content.controls.append(
                        ft.Container(
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=6,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                            on_click=fazer_clique(nome),
                            content=ft.Text(nome, size=14),
                        )
                    )
            total = len(container_resultados.content.controls)
            container_resultados.height = min(total, 5) * 44
            page.update()

        campo_pesquisa_planta.on_change = filtrar

        campo_data = ft.TextField(
            label="Data de Plantio",
            hint_text="DD/MM/AAAA",
            value=datetime.today().strftime('%d/%m/%Y'),
            dense=True
        )

        dialogo = ft.AlertDialog(title=ft.Text("Plantar no Canteiro"))

        def fechar(ev):
            dialogo.open = False
            page.update()

        def salvar(ev):
            if not planta_selecionada["nome"]:
                texto_selecionada.value = "⚠ Selecione uma planta"
                texto_selecionada.color = ft.Colors.RED
                page.update()
                return

            try:
                datetime.strptime(campo_data.value, '%d/%m/%Y')
            except ValueError:
                campo_data.error_text = "Use o formato DD/MM/AAAA"
                page.update()
                return

            nome_planta = planta_selecionada["nome"]
            dados_planta = plantas_db.get(nome_planta, {'colheita': 90, 'rega': 1})

            novo_dict = {
                "nome": nome_planta,
                "data_plantio": campo_data.value,
                "ultima_rega": "Ainda não regada"
            }

            nova_planta_ui = criar_planta_visual(novo_dict, dados_planta['colheita'], dados_planta['rega'])
            lista_plantas.controls.append(nova_planta_ui)
            dados_do_canteiro["plantas"].append(novo_dict)
            
            atualizar_contagem()
            dialogo.open = False
            page.update()

        dialogo.content = ft.Container(
            width=300,
            content=ft.Column([
                campo_pesquisa_planta,
                container_resultados,
                texto_selecionada,
                campo_data,
            ], spacing=8, tight=True)
        )
        dialogo.actions = [
            ft.TextButton("Cancelar", on_click=fechar),
            ft.Button("Plantar", on_click=salvar, bgcolor="#158B32", color="white")
        ]

        try:
            if dialogo not in page.overlay:
                page.overlay.append(dialogo)
            
            dialogo.open = True
            page.update()
        except Exception as erro_dialogo:
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao abrir: {erro_dialogo}"))
            page.snack_bar.open = True
            page.update()

        if dialogo not in page.overlay:
            page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    def apagar_canteiro(e):
        if cartao_visual in coluna_canteiros.controls:
            coluna_canteiros.controls.remove(cartao_visual)
            page.update()

    def fechar_dialogo_excluir(e):
        dialogo_confirmacao.open = False
        page.update()

    def confirmar_exclusao(e):
        apagar_canteiro(e)
        fechar_dialogo_excluir(e)

    dialogo_confirmacao = ft.AlertDialog(
        bgcolor='#E5FADE',
        title=ft.Text("Atenção"),
        content=ft.Text("Tem certeza que deseja excluir este canteiro e todas as suas plantas?"),
        actions=[
            ft.TextButton("Cancelar", on_click=fechar_dialogo_excluir),
            ft.TextButton("Excluir", on_click=confirmar_exclusao, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def abrir_dialogo_excluir(e):
        if dialogo_confirmacao not in page.overlay:
            page.overlay.append(dialogo_confirmacao)
        dialogo_confirmacao.open = True
        page.update()

    botao_excluir_canteiro = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        icon_color=ft.Colors.GREY_700,
        tooltip="Excluir Canteiro",
        on_click=abrir_dialogo_excluir,
    )

    cartao_visual = ft.Card(
        data=dados_do_canteiro,
        bgcolor = '#DEFAE5',
        elevation=2,
        content=ft.Container(
            padding=10,
            content=ft.Row(
                controls=[
                    cast(List[ft.Control], ft.Column(
                        controls=cast(List[ft.Control], [
                            
                            ft.Row(
                                controls=[
                                    titulo_interativo, 
                                    titulo_input, 
                                    botao_excluir_canteiro
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=0
                            ),
                            
                            contador_plantas,
                            ft.Divider(height=1, color=ft.Colors.GREY_200),
                            lista_plantas,
                        ]),
                        expand=True,
                    )),
                    cast(List[ft.Control], ft.Row(
                        controls=cast(List[ft.Control], [
                            ft.IconButton(
                                icon=ft.Icons.ADD,
                                icon_color='#158B32',
                                tooltip="Adicionar Planta",
                                on_click=abrir_dialogo_plantio,
                            ),
                            ft.ReorderableDragHandle(
                                content=ft.Icon(ft.Icons.DRAG_HANDLE, color=ft.Colors.GREY_400),
                                mouse_cursor=ft.MouseCursor.GRAB,
                            ),
                        ]),
                        spacing=0,
                    )),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
    )

    atualizar_contagem()
    return cartao_visual


def gerar_lista_saberes(page=None, painel_info=None):
    # Use db module to read plants (ensures initial data is applied)
    try:
        from db import read_all_plants
    except Exception:
        read_all_plants = None

    lista_visual = ft.ListView(expand=True, spacing=10)

    plantas_por_tipo = {}
    try:
        plantas = read_all_plants() if read_all_plants else []
        for linha in plantas:
            if not linha or not linha.get('Tipo') or str(linha.get('Tipo')).strip() == "":
                continue
            tipo = str(linha['Tipo']).strip()
            if tipo not in plantas_por_tipo:
                plantas_por_tipo[tipo] = []
            plantas_por_tipo[tipo].append(linha)
            
        for tipo, plantas in plantas_por_tipo.items():
            lista_de_cartoes = []
            
            for planta in plantas:
                def fazer_clique(dados_planta):
                    def on_click(e):
                        if page and painel_info:
                            abrir_info_planta(page, painel_info, dados_planta)
                    return on_click

                cartao = ft.Card(
                    elevation=1,
                    content=ft.Container(
                        bgcolor="#F0FAF0",
                        padding=15,
                        border_radius=6,
                        on_click=fazer_clique(dict(planta)),
                        content=ft.Row([
                            ft.Text(planta['Nome da Planta'], weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.GREEN_900),
                            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREEN_700),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    )
                )
                lista_de_cartoes.append(cartao)
            
            pasta_categoria = ft.ExpansionTile(
                title=ft.Text(tipo, weight=ft.FontWeight.BOLD, size=18, color=ft.Colors.BLACK),
                leading=ft.Icon(ft.Icons.FOLDER, color='#158B32'),
                controls=lista_de_cartoes,
                controls_padding=ft.Padding.only(left=15, right=0, top=0, bottom=10),
            )
            lista_visual.controls.append(pasta_categoria)
                
    except FileNotFoundError:
        lista_visual.controls.append(
            ft.Text("O arquivo plantas.csv não foi encontrado na pasta.", color=ft.Colors.RED)
        )
        
    return lista_visual

def abrir_info_planta(page, painel_info, dados):
    def fechar(e):
        painel_info.visible = False
        page.update()

    # Filtra os nomes populares, limpando espaços em branco
    nomes_populares = [dados.get(f'Nome Popular {i}', '') for i in range(1, 4)]
    nomes_populares = [n.strip() for n in nomes_populares if n.strip()]

    # Filtra as plantas companheiras
    bem = [dados.get(f'Planta que Cresce Bem Junto {i}', '') for i in range(1, 4)]
    bem = [b.strip() for b in bem if b.strip()]

    # Filtra as plantas antagônicas
    mal = [dados.get(f'Planta que Cresce Mal Junto {i}', '') for i in range(1, 4)]
    mal = [m.strip() for m in mal if m.strip()]

    # Tenta 'Fonte' (plantas do usuário) e depois 'Fonte 1/2/3' (plantas de fábrica)
    fontes_lista = []
    fonte_simples = dados.get('Fonte', '').strip()
    if fonte_simples:
        fontes_lista = [f.strip() for f in fonte_simples.split(';') if f.strip()]
    else:
        for i in range(1, 4):
            f = dados.get(f'Fonte {i}', '').strip()
            if f:
                fontes_lista.append(f)
    fontes_texto = '; '.join(fontes_lista) if fontes_lista else ''

    # --- 1. Lógica Inteligente para Colheita e Rega ---
    val_colheita = str(dados.get('Tempo de Colheita (Em Dias)', '')).strip()
    if val_colheita.isdigit():
        texto_colheita = f"{val_colheita} dias"
        rotulo_colheita = "Tempo de Colheita"
    else:
        texto_colheita = val_colheita
        rotulo_colheita = "Colheita / Frutificação"

    val_rega = str(dados.get('Frequência de Rega (Em Dias)', '')).strip()
    if val_rega.isdigit():
        texto_rega = f"A cada {val_rega} dias"
    else:
        texto_rega = val_rega
        
    val_sol = str(dados.get('Quantidade de Sol', '')).strip()

    # --- 2. Ocultação de Campos Vazios ---
    def linha_info(rotulo, valor):
        # Se estiver vazio ou for explicitamente "N/A", não constrói a linha
        if not valor or str(valor).strip() == '' or str(valor).strip().upper() == 'N/A':
            return None
            
        return ft.Column([
            ft.Text(rotulo, size=12, color=ft.Colors.GREY_600),
            ft.Text(valor, size=14, weight=ft.FontWeight.W_500),
            ft.Divider(height=1),
        ], spacing=2)

    # Monta todos os blocos e remove os "None" da lista final
    todas_as_linhas = [
        linha_info("Categoria", dados.get('Tipo', '')),
        linha_info("Nomes Populares", ", ".join(nomes_populares)),
        linha_info("Quantidade de Sol", val_sol),
        linha_info(rotulo_colheita, texto_colheita),
        linha_info("Frequência de Rega", texto_rega),
        linha_info("Cresce bem com", ", ".join(bem)),
        linha_info("Cresce mal com", ", ".join(mal)),
        linha_info("Fontes", fontes_texto),
    ]
    
    linhas_visiveis = [linha for linha in todas_as_linhas if linha is not None]

    # --- 3. Tamanho da Caixa Dinâmico ---
    # Multiplica a quantidade de linhas por ~55 pixels, limitando a um máximo de 400 pixels
    altura_calculada = min(len(linhas_visiveis) * 55, 400)

    painel_info.content = ft.Column(
        controls=[
            ft.Row([
                ft.Text(dados.get('Nome da Planta', ''), size=20, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.CLOSE, on_click=fechar),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Column(
                scroll=ft.ScrollMode.AUTO,
                height=altura_calculada, 
                controls=linhas_visiveis
            ),
        ],
        tight=True  # Garante que a coluna principal abrace o tamanho do conteúdo e não deixe espaços mortos
    )
    
    painel_info.visible = True
    page.update()