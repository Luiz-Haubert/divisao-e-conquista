"""
escalonamento de tarefas com duracao, prazo e multa (divisao e conquista)

parte 3 do trabalho. o problema eh o mesmo da pd: um processador, cada tarefa tem
duracao, prazo e multa, e a gente quer a menor multa total.

tem duas coisas aqui:

  dc_direto: a tentativa mais obvia de divisao e conquista. divide as tarefas no meio,
  resolve cada metade sozinha e junta. nao da certo sempre porque as duas metades
  disputam a mesma agenda, entao os subproblemas nao sao independentes de verdade.
  serve pra mostrar o problema.

  dc_corte: a versao que funciona. antes de resolver as metades ela descobre em que
  instante a primeira metade termina de usar a agenda (o "corte"). sabendo o corte,
  a metade da esquerda fica com o tempo de inicio ate o corte e a da direita com o
  tempo do corte ate o fim, ai elas viram independentes de verdade. eh a ideia do
  hirschberg, usada pra montar a resposta da pd gastando pouca memoria.
"""

from bisect import insort

from programacao_dinamica import ordenar_por_prazo, montar_resultado


# ------------------------------------------------------------------ versao que funciona

def dc_corte(tarefas, registrar_arvore=False):
    """
    resolve o problema todo com divisao e conquista.
    devolve o mesmo ResultadoD da pd, com as contagens em info.
    """
    ordem = ordenar_por_prazo(tarefas)
    n = len(ordem)
    # mesmo limite da pd: nada termina depois do maior prazo nem depois da soma das duracoes
    T = min(max((t.prazo for t in ordem), default=0), sum(t.duracao for t in ordem))
    T = max(T, 0)

    contagem = {"chamadas": 0, "divisoes": 0, "casos_base": 0, "profundidade": 0}
    arvore = []   # cada no da recursao, so pra desenhar no teste pequeno

    def resolver(ini, fim, comeco, limite, nivel):
        """
        subproblema: escolher tarefas de ordem[ini:fim] que rodam a partir do instante
        'comeco' e terminam ate o instante 'limite'. devolve (multa evitada, tarefas escolhidas).
        """
        contagem["chamadas"] += 1
        contagem["profundidade"] = max(contagem["profundidade"], nivel)
        no = {"nivel": nivel, "ini": ini, "fim": fim, "comeco": comeco, "limite": limite}
        if registrar_arvore:
            arvore.append(no)

        # caso base 1: nenhuma tarefa ou nenhum tempo sobrando
        if fim - ini == 0 or limite - comeco <= 0:
            contagem["casos_base"] += 1
            no.update(tipo="base", valor=0, escolhidas=[])
            return 0, []

        # caso base 2: uma tarefa so, eh so ver se ela cabe
        if fim - ini == 1:
            contagem["casos_base"] += 1
            tarefa = ordem[ini]
            if comeco + tarefa.duracao <= min(tarefa.prazo, limite):
                no.update(tipo="base", valor=tarefa.multa, escolhidas=[tarefa])
                return tarefa.multa, [tarefa]
            no.update(tipo="base", valor=0, escolhidas=[])
            return 0, []

        # dividir: corta a fila de tarefas no meio
        contagem["divisoes"] += 1
        meio = (ini + fim) // 2
        largura = limite - comeco

        # esquerda[e] = maior multa evitada pela metade da esquerda terminando exatamente
        # no instante comeco + e (-1 quando nao da pra terminar ali)
        esquerda = [-1] * (largura + 1)
        esquerda[0] = 0
        for tarefa in ordem[ini:meio]:
            d = tarefa.duracao
            maior_fim = min(tarefa.prazo, limite) - comeco
            # de tras pra frente pra nao usar a mesma tarefa duas vezes
            for e in range(maior_fim, d - 1, -1):
                if esquerda[e - d] >= 0 and esquerda[e - d] + tarefa.multa > esquerda[e]:
                    esquerda[e] = esquerda[e - d] + tarefa.multa

        # direita[s] = maior multa evitada pela metade da direita comecando no instante
        # comeco + s (eh a mesma conta da linha da pd, so que so pra essa metade)
        direita = [0] * (largura + 1)
        for tarefa in reversed(ordem[meio:fim]):
            d = tarefa.duracao
            maior_inicio = min(tarefa.prazo, limite) - comeco - d
            for s in range(0, maior_inicio + 1):
                if tarefa.multa + direita[s + d] > direita[s]:
                    direita[s] = tarefa.multa + direita[s + d]

        # achar o corte: o instante onde esquerda + direita da o maior total
        melhor_total, corte = -1, 0
        for c in range(largura + 1):
            if esquerda[c] >= 0 and esquerda[c] + direita[c] > melhor_total:
                melhor_total, corte = esquerda[c] + direita[c], c
        corte_absoluto = comeco + corte
        no.update(tipo="divisao", meio=meio, corte=corte_absoluto,
                  valor_esq=esquerda[corte], valor_dir=direita[corte])
        del esquerda, direita   # nao precisa mais, libera a memoria antes de descer

        # conquistar: agora as metades sao independentes, cada uma com seu pedaco de tempo
        valor_esq, tarefas_esq = resolver(ini, meio, comeco, corte_absoluto, nivel + 1)
        valor_dir, tarefas_dir = resolver(meio, fim, corte_absoluto, limite, nivel + 1)

        # combinar: junta as duas agendas, a da esquerda vem antes
        no.update(valor=valor_esq + valor_dir, escolhidas=tarefas_esq + tarefas_dir)
        return valor_esq + valor_dir, tarefas_esq + tarefas_dir

    evitada, no_prazo = resolver(0, n, 0, T, 0)
    info = {"T": T, "evitada": evitada, "arvore": arvore, "ordem": ordem, **contagem}
    return montar_resultado(no_prazo, tarefas, info)


# ------------------------------------------------------------------ tentativa direta

def dc_direto(tarefas):
    """
    divide as tarefas no meio, resolve cada metade como se tivesse a agenda toda
    so pra ela, e na hora de juntar passa as escolhidas pelo teste do guloso
    (maior multa primeiro, entra se ainda couber). nao garante o otimo.
    """
    ordem = ordenar_por_prazo(tarefas)
    contagem = {"chamadas": 0, "divisoes": 0, "casos_base": 0, "profundidade": 0}

    def cabe(lista_por_prazo):
        tempo = 0
        for x in lista_por_prazo:
            tempo += x.duracao
            if tempo > x.prazo:
                return False
        return True

    def resolver(lista, nivel):
        contagem["chamadas"] += 1
        contagem["profundidade"] = max(contagem["profundidade"], nivel)
        # caso base: uma tarefa so, entra se cabe sozinha
        if len(lista) <= 1:
            contagem["casos_base"] += 1
            return [t for t in lista if t.duracao <= t.prazo]
        # dividir no meio e resolver cada metade sozinha
        contagem["divisoes"] += 1
        meio = len(lista) // 2
        da_esquerda = resolver(lista[:meio], nivel + 1)
        da_direita = resolver(lista[meio:], nivel + 1)
        # combinar: as duas metades acharam que tinham a agenda inteira, entao pode
        # nao caber tudo junto. passa pelo teste do guloso pra tirar o que sobra
        aceitas = []
        for tarefa in sorted(da_esquerda + da_direita, key=lambda t: t.multa, reverse=True):
            teste = aceitas[:]
            insort(teste, tarefa, key=lambda t: t.prazo)
            if cabe(teste):
                aceitas = teste
        return aceitas

    no_prazo = resolver(ordem, 0)
    return montar_resultado(no_prazo, tarefas, contagem)
