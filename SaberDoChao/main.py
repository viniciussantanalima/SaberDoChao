# main.py

import traceback
import flet as ft

try:
    import os
    import shutil
    import platform
    import csv
    import json
    import tempfile
    import db
    from typing import List, cast

    from functions import criar_canteiro, reordenar_canteiros, gerar_lista_saberes, abrir_info_planta, obter_caminho_csv, normalizar_linha_csv, abrir_csv_com_dicionarios
    from dados_iniciais import CSV_FABRICA  

    def main(page: ft.Page):
        try:
            caminho_csv_trabalho = obter_caminho_csv()
            try:
                db.ensure_csv_exists()
            except Exception as e:
                print(f"Erro ao garantir CSV inicial: {e}")
                pass

            page.title = 'Saber do Chão'
            page.theme = ft.Theme(
                navigation_bar_theme=ft.NavigationBarTheme(
                    bgcolor='#1BB241',
                    indicator_color='white',
                    label_text_style=ft.TextStyle(color='white'),
                )
            )
            page.theme_mode = ft.ThemeMode.LIGHT
            page.padding = 20

            campo_pesquisa = ft.TextField(
                hint_text="Procurar...",
                hint_style=ft.TextStyle(color=ft.Colors.BLACK_54),
                border=ft.InputBorder.NONE,
                expand=True,
                dense=True,
                content_padding=ft.Padding.symmetric(vertical=10),
                color=ft.Colors.BLACK,
                cursor_color=ft.Colors.BLACK,
                on_change=lambda e: realizar_pesquisa()
            )

            def fechar_painel_json(ev=None):
                painel_json.visible = False
                page.update()

            painel_json = ft.Container(
                visible=False,
                bgcolor=ft.Colors.WHITE,
                border_radius=20,
                padding=20,
                bottom=80,
                left=10,
                right=10,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK_26),
                content=ft.Column(
                    controls=[
                        ft.Text("", size=13),
                        ft.TextButton("Fechar", on_click=fechar_painel_json),
                    ]
                ),
            )

            def coletar_dados_exportacao():
                dados_exportacao = {"plantas_usuario": [], "canteiros": []}

                try:
                    with open(caminho_csv_trabalho, mode='r', encoding='utf-8-sig', newline='') as arquivo:
                        reader = csv.DictReader(arquivo, delimiter=';')
                        for linha in reader:
                            normalized = {str(k).strip().lstrip('\ufeff'): (v if v is not None else "") for k, v in linha.items() if k is not None}
                            fonte = normalized.get('Fonte 1') or normalized.get('Fonte', '')
                            if fonte and str(fonte).strip().lower() in {"usuário", "usuario"}:
                                dados_exportacao["plantas_usuario"].append(normalized)
                except Exception:
                    pass

                for canteiro in coluna_canteiros.controls:
                    if hasattr(canteiro, 'data') and isinstance(canteiro.data, dict) and "nome" in canteiro.data:
                        dados_exportacao["canteiros"].append({
                            "nome": canteiro.data["nome"],
                            "plantas": canteiro.data["plantas"]
                        })

                return dados_exportacao

            def salvar_json_exportado(json_texto: str):
                caminhos = []
                pasta_base = os.path.dirname(caminho_csv_trabalho) or os.getcwd()
                if pasta_base:
                    caminhos.append(pasta_base)
                caminhos.extend([
                    os.path.join(os.path.expanduser("~"), ".saberdochao"),
                    tempfile.gettempdir(),
                    os.getcwd(),
                ])

                for pasta in caminhos:
                    try:
                        os.makedirs(pasta, exist_ok=True)
                        caminho_arquivo = os.path.join(pasta, "saberes_compartilhados.json")
                        with open(caminho_arquivo, "w", encoding="utf-8") as f:
                            f.write(json_texto)
                        return caminho_arquivo
                    except Exception:
                        continue
                return None

            def compartilhar_dados(e):
                dados_exportacao = coletar_dados_exportacao()
                json_texto = json.dumps(dados_exportacao, ensure_ascii=False, indent=4)
                caminho_arquivo = salvar_json_exportado(json_texto)

                if caminho_arquivo:
                    aviso = f"✓ Arquivo salvo em: {caminho_arquivo}\n{len(dados_exportacao['canteiros'])} canteiro(s) exportados."
                else:
                    aviso = "⚠ Não foi possível salvar o arquivo automaticamente. Você pode copiar o conteúdo abaixo."

                def fechar(ev=None):
                    painel_json.visible = False
                    page.update()

                def copiar_codigo(ev=None):
                    try:
                        page.set_clipboard(json_texto)
                        page.snack_bar = ft.SnackBar(ft.Text("JSON copiado para a área de transferência"))
                    except Exception as erro:
                        page.snack_bar = ft.SnackBar(ft.Text(f"Não foi possível copiar automaticamente: {erro}"))
                    page.snack_bar.open = True
                    page.update()

                painel_json.content = ft.Column(
                    controls=[
                        ft.Text("JSON Exportado", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(aviso, size=13),
                        ft.Text(
                            "Copie os dados no botão abaixo e cole num Bloco de Notas, WhatsApp ou Email para compartilhar.",
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Row([
                            ft.TextButton("Copiar Código", icon=ft.Icons.COPY, on_click=copiar_codigo),
                            ft.TextButton("Fechar", on_click=fechar),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ]
                )
                painel_json.visible = True
                page.update()

            seletor_arquivos = None

            def processar_dados_importados(dados: dict):
                plantas_novas = dados.get("plantas_usuario", [])
                nomes_existentes = set()
                try:
                    with open(caminho_csv_trabalho, mode='r', encoding='utf-8-sig', newline='') as arquivo:
                        reader = csv.DictReader(arquivo, delimiter=';')
                        for linha in reader:
                            normalized = {str(k).strip().lstrip('\ufeff'): (v if v is not None else "") for k, v in linha.items() if k is not None}
                            nome = normalized.get('Nome da Planta', '')
                            if nome:
                                nomes_existentes.add(nome.strip().lower())
                except FileNotFoundError:
                    pass

                novas_linhas = []
                for p in plantas_novas:
                    nome_planta = p.get('Nome da Planta', '').strip()
                    if nome_planta and nome_planta.lower() not in nomes_existentes:
                        linha_csv = f"{nome_planta};{p.get('Tipo','')};{p.get('Nome Popular 1','')};{p.get('Nome Popular 2','')};{p.get('Nome Popular 3','')};{p.get('Tempo de Colheita (Em Dias)','')};{p.get('Frequência de Rega (Em Dias)','')};{p.get('Quantidade de Sol','')};{p.get('Planta que Cresce Bem Junto 1','')};{p.get('Planta que Cresce Bem Junto 2','')};{p.get('Planta que Cresce Bem Junto 3','')};{p.get('Planta que Cresce Mal Junto 1','')};{p.get('Planta que Cresce Mal Junto 2','')};{p.get('Planta que Cresce Mal Junto 3','')};{p.get('Fonte 1', p.get('Fonte', 'Usuário'))};;\n"
                        novas_linhas.append(linha_csv)

                if novas_linhas:
                    try:
                        with open(caminho_csv_trabalho, mode='a', encoding='utf-8') as arquivo:
                            for linha in novas_linhas:
                                arquivo.write(linha)
                    except Exception:
                        pass

                    refresh_saberes()

                canteiros_novos = dados.get("canteiros", [])
                if not canteiros_novos:
                    aviso_vazio = ft.AlertDialog(
                        title=ft.Text("Aviso"),
                        content=ft.Text("O arquivo selecionado não contém canteiros.")
                    )
                    def fechar_vazio(ev):
                        aviso_vazio.open = False
                        page.update()
                    aviso_vazio.actions = [ft.TextButton("Entendi", on_click=fechar_vazio)]
                    if aviso_vazio not in page.overlay:
                        page.overlay.append(aviso_vazio)
                    aviso_vazio.open = True
                    page.update()
                    return

                dialogo_opcao = ft.AlertDialog(
                    title=ft.Text("Importar Canteiros", color=ft.Colors.GREEN_700),
                    content=ft.Text(f"O arquivo contém {len(canteiros_novos)} canteiro(s).\n\nDeseja mantê-los junto com os seus canteiros atuais ou apagar os seus para colocar os novos?")
                )

                def aplicar_canteiros(substituir: bool):
                    if substituir:
                        coluna_canteiros.controls.clear()
                    for c_dados in canteiros_novos:
                        nome_cant = c_dados.get("nome", "Canteiro Importado")
                        plantas_json = c_dados.get("plantas", [])
                        novo_cant = criar_canteiro(
                            page,
                            coluna_canteiros,
                            nome_cant,
                            plantas_iniciais=plantas_json
                        )
                        coluna_canteiros.controls.append(novo_cant)

                    nonlocal contador_novos
                    contador_novos += len(canteiros_novos)
                    dialogo_opcao.open = False

                    aviso_sucesso = ft.AlertDialog(
                        title=ft.Text("Importação Concluída!", color=ft.Colors.GREEN_700),
                        content=ft.Text(f"Foram importados {len(canteiros_novos)} canteiros com sucesso!")
                    )
                    def fechar_aviso(ev):
                        aviso_sucesso.open = False
                        page.update()
                    aviso_sucesso.actions = [ft.TextButton("Entendi", on_click=fechar_aviso)]
                    if aviso_sucesso not in page.overlay:
                        page.overlay.append(aviso_sucesso)
                    aviso_sucesso.open = True
                    page.update()

                def btn_adicionar(ev):
                    aplicar_canteiros(substituir=False)

                def btn_substituir(ev):
                    aplicar_canteiros(substituir=True)

                def fechar_opcao(ev):
                    dialogo_opcao.open = False
                    page.update()

                dialogo_opcao.actions = [
                    ft.TextButton("Cancelar", on_click=fechar_opcao),
                    ft.TextButton("Adicionar Juntos", on_click=btn_adicionar),
                    ft.Button("Substituir Todos", on_click=btn_substituir, bgcolor=ft.Colors.RED, color="white")
                ]
                if dialogo_opcao not in page.overlay:
                    page.overlay.append(dialogo_opcao)
                dialogo_opcao.open = True
                page.update()

            def mostrar_importacao_manual():
                campo_json_importacao = ft.TextField(
                    label="Cole aqui o JSON de importação",
                    multiline=True,
                    min_lines=10,
                    expand=True,
                    border=ft.InputBorder.OUTLINE,
                    hint_text='{"plantas_usuario": [], "canteiros": []}'
                )

                dialogo_manual = ft.AlertDialog(
                    title=ft.Text("Importação Manual", color=ft.Colors.GREEN_700),
                    content=ft.Column([campo_json_importacao], spacing=10),
                )

                def fechar_manual(ev):
                    dialogo_manual.open = False
                    page.update()

                def importar_manual(ev):
                    texto = campo_json_importacao.value or ""
                    try:
                        dados = json.loads(texto)
                    except Exception as ex:
                        campo_json_importacao.error_text = "JSON inválido"
                        page.update()
                        return
                    dialogo_manual.open = False
                    page.update()
                    processar_dados_importados(dados)

                dialogo_manual.actions = [
                    ft.TextButton("Cancelar", on_click=fechar_manual),
                    ft.TextButton("Importar", on_click=importar_manual),
                ]
                if dialogo_manual not in page.overlay:
                    page.overlay.append(dialogo_manual)
                dialogo_manual.open = True
                page.update()

            def mostrar_dialogo_filepicker_indisponivel(mensagem: str):
                aviso_nd = ft.AlertDialog(
                    title=ft.Text("Importar Arquivo", color=ft.Colors.ORANGE),
                    content=ft.Text(mensagem)
                )
                def fechar_nd(ev):
                    aviso_nd.open = False
                    page.update()
                def abrir_manual(ev):
                    aviso_nd.open = False
                    page.update()
                    mostrar_importacao_manual()
                aviso_nd.actions = [
                    ft.TextButton("Importação Manual", on_click=abrir_manual),
                    ft.TextButton("Fechar", on_click=fechar_nd)
                ]
                if aviso_nd not in page.overlay:
                    page.overlay.append(aviso_nd)
                aviso_nd.open = True
                page.update()

            async def realizar_importacao_arquivo(e):
                nonlocal seletor_arquivos

                if not seletor_arquivos:
                    try:
                        seletor_arquivos = ft.FilePicker()
                        page.overlay.append(seletor_arquivos)
                    except Exception as ex:
                        print(f"[main] FilePicker não disponível: {ex}")
                        mostrar_dialogo_filepicker_indisponivel(
                            "A importação de ficheiros está restrita pelo Android.\n"
                            "Utilize a colagem manual do código."
                        )
                        return

                try:
                    files = await seletor_arquivos.pick_files(
                        allow_multiple=False,
                        allowed_extensions=["json"]
                    )
                except Exception as ex:
                    print(f"[main] FilePicker falhou ao abrir: {ex}")
                    mostrar_dialogo_filepicker_indisponivel(
                        "O seletor de ficheiros falhou.\n"
                        "Utilize a importação manual para continuar."
                    )
                    return

                if not files:
                    return

                try:
                    if files[0].path:
                        with open(files[0].path, 'r', encoding='utf-8') as f:
                            conteudo = f.read()
                    elif hasattr(files[0], 'bytes') and files[0].bytes:
                        conteudo = files[0].bytes.decode('utf-8')
                    else:
                        return

                    dados = json.loads(conteudo)
                    processar_dados_importados(dados)
                except Exception as erro:
                    aviso_erro = ft.AlertDialog(
                        title=ft.Text("Erro na Importação", color=ft.Colors.RED),
                        content=ft.Text(f"Ocorreu um erro ao ler o arquivo:\n\n{erro}")
                    )
                    def fechar_erro(ev):
                        aviso_erro.open = False
                        page.update()
                    aviso_erro.actions = [ft.TextButton("Fechar", on_click=fechar_erro)]

                    if aviso_erro not in page.overlay:
                        page.overlay.append(aviso_erro)
                    aviso_erro.open = True
                    page.update()

            topo_ferramentas = ft.Row(
                controls=cast(List[ft.Control], [
                    ft.Icon(ft.CupertinoIcons.ANT_FILL, color='#158B32', size=24),
                    ft.Container(
                        expand=True,
                        border=ft.Border.only(bottom=ft.BorderSide(1, '#158B32')),
                        content=ft.Row(
                            controls=cast(List[ft.Control], [
                                ft.Container(
                                    content=ft.Icon(ft.Icons.SEARCH, color='#158B32', size=20),
                                    alignment=ft.Alignment.CENTER,
                                    padding=ft.Padding.symmetric(horizontal=10),
                                ),
                                campo_pesquisa,
                            ]),
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ),
                    ft.Container(
                        bgcolor = "#158B32",
                        border_radius=30,
                        content=ft.IconButton(
                            icon=ft.Icons.FILE_UPLOAD, 
                            icon_color='white', 
                            tooltip="Importar Arquivo JSON",
                            on_click=realizar_importacao_arquivo
                        )
                    ),
                    ft.Container(
                        bgcolor = '#158B32',
                        border_radius=30,
                        content=ft.IconButton(
                            icon=ft.Icons.SHARE, 
                            icon_color='white', 
                            tooltip="Compartilhar JSON",
                            on_click=compartilhar_dados
                        )
                    )
                ]),
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

            topo_ferramentas_box = ft.Container(
                content=topo_ferramentas,
                bgcolor="#E5FADE",
                padding=ft.Padding.all(12),
                border_radius=ft.BorderRadius.all(30),
                shadow=ft.BoxShadow(blur_radius=8, offset=ft.Offset(0, 2), color=ft.Colors.GREY_300),
            )

            botao_ajuda = ft.Container(
                content=ft.Button(
                    "Precisa de Ajuda?", 
                    bgcolor='#158B32', 
                    color='white',
                    on_click=lambda _: mudar_aba(2)
                ),
                alignment=ft.Alignment.CENTER,
            )

            coluna_canteiros = ft.ReorderableListView(
                expand=True,
                spacing=10,
                padding=ft.Padding.symmetric(vertical=10),
                show_default_drag_handles=False,
                on_reorder=lambda e: reordenar_canteiros(e, coluna_canteiros, page),
            )

            contador_novos = 1

            def adicionar_novo_canteiro(e):
                nonlocal contador_novos
                novo = criar_canteiro(
                    page,
                    coluna_canteiros,
                    f"Novo Canteiro {contador_novos}",
                    plantas_iniciais=[],
                )
                coluna_canteiros.controls.append(novo)
                contador_novos += 1
                page.update()

            page.floating_action_button = ft.FloatingActionButton(
                content=ft.Icon(ft.Icons.ADD, color='white'), 
                bgcolor='#158B32',
                on_click=adicionar_novo_canteiro,
                tooltip="Registrar Novo Canteiro",
            )

            lista_resultados_culturas = ft.ListView(expand=True, spacing=10, visible=False)
            lista_resultados_saberes = ft.ListView(expand=True, spacing=10, visible=False)

            tela_culturas = ft.Column(
                controls=cast(List[ft.Control], [
                    ft.Text("Meus Canteiros", size=24, weight=ft.FontWeight.BOLD),
                    coluna_canteiros,
                    lista_resultados_culturas,
                ]),
                visible=True,
                expand=True,
            )

            painel_info = ft.Container(
                visible=False,
                bgcolor=ft.Colors.WHITE,
                border_radius=20,
                padding=20,
                bottom=50,
                left=10,
                right=10,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK_26), 
                content=ft.Text(""),
            )

            def refresh_saberes():
                container_lista_saberes.content = gerar_lista_saberes(
                    page,
                    painel_info,
                    on_planta_alterada=refresh_saberes,
                )
                page.update()

            container_lista_saberes = ft.Container(
                content=gerar_lista_saberes(page, painel_info, on_planta_alterada=refresh_saberes),
                expand=True
            )

            painel_form = ft.Container(
                visible=False,
                bgcolor=ft.Colors.WHITE,
                border_radius=20,
                padding=20,
                bottom=50,
                left=10,
                right=10,
                shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK_26),
                content=ft.Text(""),
            )

            def abrir_form_planta(e):
                nomes_existentes = []
                try:
                    with open(caminho_csv_trabalho, mode='r', encoding='utf-8-sig', newline='') as arquivo:
                        reader = csv.DictReader(arquivo, delimiter=';')
                        for linha in reader:
                            normalized = {str(k).strip().lstrip('\ufeff'): (v if v is not None else "") for k, v in linha.items() if k is not None}
                            nome = normalized.get('Nome da Planta', '').strip()
                            if nome:
                                nomes_existentes.append(nome)
                except FileNotFoundError:
                    pass

                campo_nome_planta = ft.TextField(label="Nome da Planta *", dense=True)
                campo_tipo_planta = ft.Dropdown(
                    label="Categoria *",
                    dense=True,
                    options=[
                        ft.dropdown.Option("Alimentícias"),
                        ft.dropdown.Option("Medicinais/Chás"),
                        ft.dropdown.Option("Religiosidades"),
                        ft.dropdown.Option("Ornamentais"),
                        ft.dropdown.Option("Agroflorestais"),
                        ft.dropdown.Option("Outras")
                    ]
                )
                campo_pop = ft.TextField(label="Nomes Populares (separados por vírgula)", dense=True)
                campo_colheita = ft.TextField(label="Tempo de Colheita (Dias) / Período de Frutificação (Mês - Mês)*", dense=True, input_filter=ft.NumbersOnlyInputFilter())
                campo_rega = ft.TextField(label="Frequência de Rega (Dias) *", dense=True, input_filter=ft.NumbersOnlyInputFilter())
                campo_quant_sol = ft.Dropdown(
                    label="Quantidade de Sol",
                    dense=True,
                    options=[
                        ft.dropdown.Option("Sol Pleno"),
                        ft.dropdown.Option("Meia-Sombra"),
                        ft.dropdown.Option("Sombra")
                    ]
                )
                checks_bem = [ft.Checkbox(label=nome) for nome in nomes_existentes]
                checks_mal = [ft.Checkbox(label=nome) for nome in nomes_existentes]

                def fechar(ev):
                    painel_form.visible = False
                    page.update()

                def salvar(ev):
                    if not campo_nome_planta.value or not campo_tipo_planta.value or not campo_quant_sol.value or not campo_colheita.value or not campo_rega.value:
                        campo_nome_planta.error_text = "Obrigatório" if not campo_nome_planta.value else None
                        campo_tipo_planta.error_text = "Obrigatório" if not campo_tipo_planta.value else None
                        campo_colheita.error_text = "Obrigatório" if not campo_colheita.value else None
                        campo_rega.error_text = "Obrigatório" if not campo_rega.value else None
                        page.update()
                        return

                    painel_form.visible = False

                    pops = [p.strip() for p in campo_pop.value.split(",")] if campo_pop.value else []
                    while len(pops) < 3: pops.append("")
                    bem = [c.label for c in checks_bem if c.value][:3]
                    while len(bem) < 3: bem.append("")
                    mal = [c.label for c in checks_mal if c.value][:3]
                    while len(mal) < 3: mal.append("")

                    plant = {
                        'Nome da Planta': campo_nome_planta.value.strip(),
                        'Tipo': campo_tipo_planta.value or '',
                        'Nome Popular 1': pops[0],
                        'Nome Popular 2': pops[1],
                        'Nome Popular 3': pops[2],
                        'Tempo de Colheita (Em Dias)': campo_colheita.value or '',
                        'Frequência de Rega (Em Dias)': campo_rega.value or '',
                        'Quantidade de Sol': campo_quant_sol.value or '',
                        'Planta que Cresce Bem Junto 1': bem[0],
                        'Planta que Cresce Bem Junto 2': bem[1],
                        'Planta que Cresce Bem Junto 3': bem[2],
                        'Planta que Cresce Mal Junto 1': mal[0],
                        'Planta que Cresce Mal Junto 2': mal[1],
                        'Planta que Cresce Mal Junto 3': mal[2],
                        'Fonte 1': 'Usuário',
                        'Fonte 2': '',
                        'Fonte 3': '',
                    }

                    added = False
                    try:
                        added = db.add_plant(plant)
                    except Exception as ex:
                        print(f"[main] Erro ao adicionar planta via db: {ex}")

                    if not added:
                        try:
                            with open(caminho_csv_trabalho, mode='a', encoding='utf-8') as arquivo:
                                arquivo.write(';'.join([plant.get(h, '') for h in [
                                    'Nome da Planta','Tipo','Nome Popular 1','Nome Popular 2','Nome Popular 3',
                                    'Tempo de Colheita (Em Dias)','Frequência de Rega (Em Dias)','Quantidade de Sol',
                                    'Planta que Cresce Bem Junto 1','Planta que Cresce Bem Junto 2','Planta que Cresce Bem Junto 3',
                                    'Planta que Cresce Mal Junto 1','Planta que Cresce Mal Junto 2','Planta que Cresce Mal Junto 3',
                                    'Fonte 1','Fonte 2','Fonte 3']]) + '\n')
                        except Exception:
                            pass

                    refresh_saberes()

                painel_form.content = ft.Column(
                    controls=[
                        ft.Row([
                            ft.Text("Registrar Nova Planta", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(ft.Icons.CLOSE, on_click=fechar),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            height=350,
                            controls=[
                                campo_nome_planta, campo_tipo_planta, campo_colheita, campo_rega, campo_pop, campo_quant_sol,
                                ft.ExpansionTile(title=ft.Text("Cresce bem com... (Até 3)"), controls=checks_bem),
                                ft.ExpansionTile(title=ft.Text("Cresce mal com... (Até 3)"), controls=checks_mal),
                            ]
                        ),
                        ft.Row([
                            ft.TextButton("Cancelar", on_click=fechar),
                            ft.Button("Salvar", on_click=salvar, bgcolor="#158B32", color="white"),
                        ]),
                    ]
                )
                painel_form.visible = True
                page.update()

            botao_nova_planta = ft.Button(
                "Adicionar Nova Planta",
                icon=ft.Icons.ADD,
                color="white",
                bgcolor="#158B32",
                on_click=abrir_form_planta
            )

            tela_saberes = ft.Column(
                controls=cast(List[ft.Control], [
                    ft.Text("Saberes", size=24, weight=ft.FontWeight.BOLD),
                    botao_nova_planta,
                    container_lista_saberes,
                    lista_resultados_saberes,
                ]),
                visible=False,
                expand=True,
            )

            tela_apoio = ft.Column(
                controls=cast(List[ft.Control], [
                    ft.Text("Apoio e Tutoriais", size=24, weight=ft.FontWeight.BOLD),
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Text("Tutorial: Como registrar um plantio"), alignment=ft.Alignment.CENTER)),
                ]),
                visible=False,
            )

            def realizar_pesquisa():
                termo = campo_pesquisa.value.lower().strip() if campo_pesquisa.value else ""
                aba_atual = page.navigation_bar.selected_index

                if not termo:
                    coluna_canteiros.visible = True
                    lista_resultados_culturas.visible = False
                    
                    container_lista_saberes.visible = True
                    lista_resultados_saberes.visible = False
                    page.update()
                    return

                if aba_atual == 0:
                    coluna_canteiros.visible = False
                    lista_resultados_culturas.visible = True
                    lista_resultados_culturas.controls.clear()
                    
                    encontrou = False
                    for canteiro in coluna_canteiros.controls:
                        if hasattr(canteiro, 'data') and isinstance(canteiro.data, dict) and "nome" in canteiro.data:
                            nome_cant = canteiro.data["nome"]
                            plantas = canteiro.data["plantas"]
                            
                            for p in plantas:
                                nome_da_planta = p["nome"]
                                if termo in nome_da_planta.lower():
                                    lista_resultados_culturas.controls.append(
                                        ft.ListTile(
                                            leading=ft.Icon(ft.Icons.ECO, color="#1BB241"),
                                            title=ft.Text(f"{nome_da_planta}, {nome_cant}", weight=ft.FontWeight.W_500)
                                        )
                                    )
                                    encontrou = True

                            if termo in nome_cant.lower():
                                lista_resultados_culturas.controls.append(
                                    ft.ListTile(
                                        leading=ft.Icon(ft.Icons.GRID_ON, color="#158B32"),
                                        title=ft.Text(f"Canteiro: {nome_cant}", weight=ft.FontWeight.BOLD)
                                    )
                                )
                                encontrou = True

                    if not encontrou:
                        lista_resultados_culturas.controls.append(ft.Text("Nenhum canteiro ou planta encontrada.", color=ft.Colors.RED))

                elif aba_atual == 1:
                    container_lista_saberes.visible = False
                    lista_resultados_saberes.visible = True
                    lista_resultados_saberes.controls.clear()
                    
                    encontrou = False
                    try:
                        with open(caminho_csv_trabalho, mode='r', encoding='utf-8-sig', newline='') as arquivo:
                            reader = csv.DictReader(arquivo, delimiter=';')
                            for linha in reader:
                                if not linha:
                                    continue
                                normalized = {str(k).strip().lstrip('\ufeff'): (v if v is not None else "") for k, v in linha.items() if k is not None}
                                if not normalized.get('Nome da Planta'):
                                    continue
                                nome_planta = str(normalized.get('Nome da Planta', '')).strip()
                                pops = [str(normalized.get(f'Nome Popular {i}', '')).strip() for i in range(1, 4) if str(normalized.get(f'Nome Popular {i}', '')).strip() != ""]
                                texto_busca = (nome_planta + " " + " ".join(pops)).lower()
                                if termo in texto_busca:
                                    encontrou = True
                                    dados = normalized
                                    def fazer_clique(d):
                                        return lambda ev: abrir_info_planta(page, painel_info, d)

                                    subtitulo = f"Conhecida como: {', '.join(pops)}" if pops else "Planta registrada"

                                    cartao = ft.Card(
                                        elevation=1,
                                        content=ft.Container(
                                            bgcolor="#F0FAF0",
                                            padding=15,
                                            border_radius=6,
                                            on_click=fazer_clique(dados),
                                            content=ft.Row([
                                                ft.Column([
                                                    ft.Text(nome_planta, weight=ft.FontWeight.BOLD, size=16, color=ft.Colors.GREEN_900),
                                                    ft.Text(subtitulo, size=12, color=ft.Colors.GREEN_700),
                                                ], spacing=2),
                                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREEN_700),
                                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                        )
                                    )
                                    lista_resultados_saberes.controls.append(cartao)
                    except FileNotFoundError:
                        pass
                        
                    if not encontrou:
                        lista_resultados_saberes.controls.append(ft.Text("Nenhuma planta encontrada com esse nome.", color=ft.Colors.RED))
                        
                page.update()

            def alternar_tema(e):
                if page.theme_mode == ft.ThemeMode.LIGHT:
                    page.theme_mode = ft.ThemeMode.DARK
                    topo_ferramentas_box.bgcolor = "#003A05"
                    topo_ferramentas_box.shadow = ft.BoxShadow(blur_radius=8, offset=ft.Offset(0, 2), color=ft.Colors.BLACK)
                    page.navigation_bar.bgcolor = "#0A4518"
                else:
                    page.theme_mode = ft.ThemeMode.LIGHT
                    topo_ferramentas_box.bgcolor = "#E5FADE" 
                    topo_ferramentas_box.shadow = ft.BoxShadow(blur_radius=8, offset=ft.Offset(0, 2), color=ft.Colors.GREY_300)
                    page.navigation_bar.bgcolor = "#1BB241"
                page.update()

            tela_config = ft.Column(
                controls=cast(List[ft.Control], [
                    ft.Text("Configurações", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Switch(label="Modo Escuro", on_change=alternar_tema),
                    ft.Divider(),
                    ft.Button("Acessibilidade e Inclusão", icon=ft.Icons.ACCESSIBILITY_NEW, width=300),
                ]),
                visible=False,
            )

            telas = [tela_culturas, tela_saberes, tela_apoio, tela_config]

            def mudar_aba(e):
                if hasattr(e, 'control'):
                    indice = e.control.selected_index
                else:
                    indice = e
                
                tela_culturas.visible = True if indice == 0 else False
                tela_saberes.visible = True if indice == 1 else False
                tela_apoio.visible = True if indice == 2 else False
                tela_config.visible = True if indice == 3 else False

                page.floating_action_button.visible = True if indice == 0 else False
                
                topo_ferramentas_box.visible = True if indice in [0, 1] else False
                botao_ajuda.visible = True if indice in [0, 1] else False
                
                page.navigation_bar.selected_index = indice
                page.update()

            page.navigation_bar = ft.NavigationBar(
                bgcolor='#1BB241',
                indicator_color='#0F6424',
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.ECO, color=ft.Colors.WHITE), label="Culturas"),
                    ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.MENU_BOOK, color=ft.Colors.WHITE), label="Saberes"),
                    ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, color=ft.Colors.WHITE), label="Apoio"),
                    ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.SETTINGS, color=ft.Colors.WHITE), label="Config"),
                ],
                on_change=mudar_aba,
                selected_index=0,
            )

            page.add(
                ft.SafeArea(
                    ft.Stack(
                        expand=True,
                        controls=[
                            ft.Column(
                                expand=True,
                                controls=[
                                    topo_ferramentas_box,
                                    botao_ajuda,
                                    ft.Divider(),
                                    *telas,
                                ]
                            ),
                            painel_form,
                            painel_info,
                            painel_json
                        ]
                    ),
                    expand=True
                )
            )

            page.update()
        
        except Exception as e:
            page.scroll = "auto"
            page.add(
                ft.SafeArea(
                    ft.Column([
                        ft.Text("CRASH INTERNO ANTES DE ABRIR:", color="red", weight="bold", size=20),
                        ft.Text(str(e), color="orange", weight="bold"),
                        ft.Text(traceback.format_exc(), color="white", size=11, selectable=True)
                    ])
                )
            )
            page.update()

    ft.app(target=main)

except Exception as erro_global:
    erro_trace = traceback.format_exc()
    def error_main(page: ft.Page):
        page.scroll = "auto"
        page.add(
            ft.SafeArea(
                ft.Column([
                    ft.Text("💥 CRASH FATAL NAS IMPORTAÇÕES:", color="red", weight="bold", size=20),
                    ft.Text("O aplicativo colapsou antes mesmo de tentar desenhar a tela.", color="white", size=14),
                    ft.Text(str(erro_global), color="orange", weight="bold"),
                    ft.Text(erro_trace, color="white", size=11, selectable=True)
                ])
            )
        )
    ft.app(target=error_main)