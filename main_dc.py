"""
testes da parte 3 do trabalho (aula 11: divisao e conquista)

como usar:
    python main_dc.py                         -> roda tudo
    python main_dc.py --teste 1               -> instancia pequena, passo a passo (arvore e cortes)
    python main_dc.py --teste 2               -> instancia media (guloso x pd x divisao e conquista)
    python main_dc.py --teste 3               -> instancias grandes (tempo e memoria)
    python main_dc.py --validar               -> confere com a forca bruta em varias instancias
    python main_dc.py --arquivo minhas.csv    -> roda com um csv (nome,duracao,prazo,multa)
"""

import argparse
import csv
import os
import platform
import random
import sys
import time
import tracemalloc

from programacao_dinamica import TarefaD, pd_bottom_up, guloso_adaptado, forca_bruta, cabe_no_prazo
from divisao_conquista import dc_corte, dc_direto
# reaproveita as funcoes de entrada e saida da parte 2
from main_pd import carregar_csv, gerar_tarefas, titulo, imprimir_agenda, SEMENTE, PASTA


def cronometrar(funcao, tarefas, repeticoes=3):
    # roda algumas vezes e fica com o menor tempo, em ms
    melhor, resultado = float("inf"), None
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        resultado = funcao(tarefas)
        melhor = min(melhor, (time.perf_counter() - inicio) * 1000)
    return melhor, resultado


def medir_memoria(funcao, tarefas):
    # pico de memoria em mb durante a execucao (rodada separada porque o tracemalloc deixa lento)
    tracemalloc.start()
    funcao(tarefas)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pico / (1024 * 1024)


def nomes(lista):
    return ", ".join(t.nome for t in lista) if lista else "nenhuma"


# ---------------------------------------------------------------- testes

def teste_pequeno():
    titulo("TESTE 1 - instância pequena (as mesmas 5 tarefas da parte 2)")
    tarefas = carregar_csv(os.path.join(PASTA, "entradas", "pd_teste1.csv"))
    print("\nEntrada:")
    for t in tarefas:
        print(f"  {t.nome}: duração {t.duracao}, prazo {t.prazo}, multa {t.multa}")

    r = dc_corte(tarefas, registrar_arvore=True)
    ordem = r.info["ordem"]
    print("\nFila por prazo: " + ", ".join(f"{i}:{t.nome}" for i, t in enumerate(ordem)))
    print(f"Agenda vai do instante 0 até {r.info['T']}")

    # mostra a conta do corte da primeira divisao
    raiz = r.info["arvore"][0]
    meio = raiz["meio"]
    print(f"\nPrimeira divisão: esquerda = {nomes(ordem[:meio])} | direita = {nomes(ordem[meio:])}")
    print("Pra achar o corte, testa cada instante t:")
    print("  esquerda(t) = quanto a esquerda evita terminando em t | direita(t) = quanto a direita evita começando em t")
    esq_dir = calcular_corte(ordem[:meio], ordem[meio:], 0, r.info["T"])
    for c, (e, d) in enumerate(esq_dir):
        if e >= 0:
            marca = "  <- corte" if c == raiz["corte"] else ""
            print(f"  t = {c}: esquerda {e:>3} + direita {d:>3} = {e + d:>3}{marca}")
        else:
            print(f"  t = {c}: a esquerda não consegue terminar exatamente aqui")

    print("\nÁrvore de recursão (tarefas | tempo disponível -> resultado):")
    for no in r.info["arvore"]:
        recuo = "    " * no["nivel"]
        grupo = nomes(ordem[no["ini"]:no["fim"]])
        faixa = f"tempo {no['comeco']} a {no['limite']}"
        if no["tipo"] == "divisao":
            print(f"{recuo}[{grupo}] {faixa} -> corte em {no['corte']}, evita {no['valor']} ({nomes(no['escolhidas'])})")
        else:
            print(f"{recuo}[{grupo}] {faixa} -> caso base, evita {no['valor']} ({nomes(no['escolhidas'])})")

    print(f"\n  Chamadas recursivas: {r.info['chamadas']} | divisões: {r.info['divisoes']} | "
          f"casos base: {r.info['casos_base']} | profundidade: {r.info['profundidade']}")
    # instancia tao pequena que precisa rodar varias vezes pra dar pra medir
    tempo, _ = cronometrar(dc_corte, tarefas, 100)
    print(f"  Tempo da divisão e conquista: {tempo:.4f} ms (menor de 100 execuções)")

    print("\nAgenda da divisão e conquista:")
    imprimir_agenda(r)

    direto = dc_direto(tarefas)
    print(f"\n  Divisão e conquista direta (sem corte): multa {direto.multa_total}, no prazo: {nomes(direto.no_prazo)}")
    print(f"  PD bottom-up: multa {pd_bottom_up(tarefas).multa_total}")
    print(f"  Guloso adaptado: multa {guloso_adaptado(tarefas).multa_total}")
    print(f"  Força bruta: multa mínima = {forca_bruta(tarefas)}")


def calcular_corte(esq, dir_, comeco, limite):
    # repete a conta do corte so pra mostrar na tela (a mesma que esta em dc_corte)
    largura = limite - comeco
    esquerda = [-1] * (largura + 1)
    esquerda[0] = 0
    for t in esq:
        for e in range(min(t.prazo, limite) - comeco, t.duracao - 1, -1):
            if esquerda[e - t.duracao] >= 0:
                esquerda[e] = max(esquerda[e], esquerda[e - t.duracao] + t.multa)
    direita = [0] * (largura + 1)
    for t in reversed(dir_):
        for s in range(0, min(t.prazo, limite) - comeco - t.duracao + 1):
            direita[s] = max(direita[s], t.multa + direita[s + t.duracao])
    return list(zip(esquerda, direita))


def teste_medio():
    n = 500
    titulo(f"TESTE 2 - instância média ({n} tarefas aleatórias, semente {SEMENTE}, a mesma da parte 2)")
    tarefas = gerar_tarefas(n)

    tempo_dc, dc = cronometrar(dc_corte, tarefas)
    tempo_pd, pd = cronometrar(pd_bottom_up, tarefas)
    tempo_g, g = cronometrar(guloso_adaptado, tarefas)
    tempo_dir, direto = cronometrar(dc_direto, tarefas)
    mem_dc, mem_pd = medir_memoria(dc_corte, tarefas), medir_memoria(pd_bottom_up, tarefas)
    mem_g = medir_memoria(guloso_adaptado, tarefas)

    print(f"\n  Divisão e conquista com corte: {dc.info['chamadas']} chamadas, {dc.info['divisoes']} divisões, "
          f"{dc.info['casos_base']} casos base, profundidade {dc.info['profundidade']}")
    print(f"  Divisão e conquista direta: {direto.info['chamadas']} chamadas, profundidade {direto.info['profundidade']}")
    print(f"\n  {'':<22} | {'no prazo':>8} | {'multa':>8} | {'tempo (ms)':>10} | {'memória (MB)':>12}")
    print("  " + "-" * 74)
    print(f"  {'D&C com corte':<22} | {len(dc.no_prazo):>8} | {dc.multa_total:>8} | {tempo_dc:>10.2f} | {mem_dc:>12.2f}")
    print(f"  {'PD bottom-up':<22} | {len(pd.no_prazo):>8} | {pd.multa_total:>8} | {tempo_pd:>10.2f} | {mem_pd:>12.2f}")
    print(f"  {'Guloso adaptado':<22} | {len(g.no_prazo):>8} | {g.multa_total:>8} | {tempo_g:>10.2f} | {mem_g:>12.2f}")
    print(f"  {'D&C direta':<22} | {len(direto.no_prazo):>8} | {direto.multa_total:>8} | {tempo_dir:>10.2f} | {'-':>12}")
    print(f"\n  D&C com corte achou a mesma multa da PD? {dc.multa_total == pd.multa_total}")
    print(f"  Agenda da D&C é viável? {cabe_no_prazo(dc.no_prazo)}")


def memoria_estimada(n, T):
    # o tracemalloc deixa as instancias grandes muito lentas, entao pra elas a gente calcula
    # o tamanho das estruturas principais: cada numero numa lista do python gasta uns 36 bytes
    # (8 do ponteiro + 28 do int), e a pd guarda 1 byte de decisao por estado
    linhas = 2 * (T + 1) * 36
    pd = n * (T + 1) + linhas          # matriz de decisoes + duas linhas de valores
    dc = linhas + n * 8                 # duas linhas (esquerda e direita) + a lista da resposta
    return dc / (1024 * 1024), pd / (1024 * 1024)


def teste_grande():
    titulo("TESTE 3 - instâncias grandes (tempo e memória)")
    print(f"Python {platform.python_version()} | {platform.system()} {platform.release()} | "
          f"{platform.processor() or platform.machine()}")
    print("Tempo em ms (menor de 3 execuções até 1.000 tarefas, 1 execução acima).")
    print("Memória estimada pelo tamanho das estruturas principais, em MB.\n")
    tamanhos = [500, 1000, 2000, 4000, 8000]
    linhas = []
    print(f"  {'n':>6} | {'T':>6} | {'D&C (ms)':>10} | {'PD (ms)':>10} | {'gul. (ms)':>9} | {'mem D&C':>8} | {'mem PD':>8} | "
          f"{'cham.':>6} | {'div.':>5} | {'prof.':>5} | {'multa D&C':>9} | {'multa PD':>9} | {'multa gul.':>10}")
    print("  " + "-" * 132)
    for n in tamanhos:
        tarefas = gerar_tarefas(n)
        rep = 3 if n < 2000 else 1
        tempo_dc, dc = cronometrar(dc_corte, tarefas, rep)
        tempo_pd, pd = cronometrar(pd_bottom_up, tarefas, rep)
        tempo_g, g = cronometrar(guloso_adaptado, tarefas, rep)
        mem_dc, mem_pd = memoria_estimada(n, dc.info["T"])
        print(f"  {n:>6} | {dc.info['T']:>6} | {tempo_dc:>10.2f} | {tempo_pd:>10.2f} | {tempo_g:>9.2f} | {mem_dc:>8.2f} | "
              f"{mem_pd:>8.2f} | {dc.info['chamadas']:>6} | {dc.info['divisoes']:>5} | {dc.info['profundidade']:>5} | "
              f"{dc.multa_total:>9} | {pd.multa_total:>9} | {g.multa_total:>10}")
        sys.stdout.flush()
        linhas.append([n, dc.info["T"], f"{tempo_dc:.2f}", f"{tempo_pd:.2f}", f"{tempo_g:.2f}", f"{mem_dc:.2f}",
                       f"{mem_pd:.2f}", dc.info["chamadas"], dc.info["divisoes"], dc.info["profundidade"],
                       dc.multa_total, pd.multa_total, g.multa_total])
    with open("resultados_tempos_dc.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["n", "T", "dc_ms", "pd_ms", "guloso_ms", "dc_mb", "pd_mb", "chamadas", "divisoes",
                           "profundidade", "multa_dc", "multa_pd", "multa_guloso"])
        escritor.writerows(linhas)
    print("\n  (tabela salva em resultados_tempos_dc.csv)")


def validar(quantidade=500):
    titulo(f"VALIDAÇÃO - comparação com a força bruta em {quantidade} instâncias aleatórias (n de 1 a 12)")
    rng = random.Random(SEMENTE)
    erros_dc = erros_direto = erros_guloso = 0
    for _ in range(quantidade):
        n = rng.randint(1, 12)
        tarefas = [TarefaD(f"T{i}", rng.randint(1, 5), rng.randint(1, 3 * n), rng.randint(1, 50))
                   for i in range(1, n + 1)]
        otimo = forca_bruta(tarefas)
        r = dc_corte(tarefas)
        if r.multa_total != otimo or not cabe_no_prazo(r.no_prazo):
            erros_dc += 1
        if dc_direto(tarefas).multa_total != otimo:
            erros_direto += 1
        if guloso_adaptado(tarefas).multa_total != otimo:
            erros_guloso += 1
    print(f"  D&C com corte NÃO achou o ótimo em: {erros_dc} de {quantidade}")
    print(f"  D&C direta NÃO achou o ótimo em: {erros_direto} de {quantidade}")
    print(f"  Guloso NÃO achou o ótimo em: {erros_guloso} de {quantidade}")


def rodar_arquivo(caminho):
    titulo(f"Arquivo: {caminho}")
    tarefas = carregar_csv(caminho)
    print("Divisão e conquista:")
    imprimir_agenda(dc_corte(tarefas))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Escalonamento com duração, prazo e multa (Divisão e Conquista)")
    parser.add_argument("--teste", type=int, choices=[1, 2, 3])
    parser.add_argument("--validar", action="store_true")
    parser.add_argument("--arquivo")
    args = parser.parse_args()

    if args.arquivo:
        rodar_arquivo(args.arquivo)
    elif args.teste == 1:
        teste_pequeno()
    elif args.teste == 2:
        teste_medio()
    elif args.teste == 3:
        teste_grande()
    elif args.validar:
        validar()
    else:
        teste_pequeno()
        validar()
        teste_medio()
        teste_grande()
