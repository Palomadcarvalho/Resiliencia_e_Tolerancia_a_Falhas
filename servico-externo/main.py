from fastapi import FastAPI
import asyncio
import re

app = FastAPI(title="Serviço Externo Simulado - Validação de CPF")


def cpf_valido(cpf: str) -> bool:
    """Valida CPF usando o algoritmo oficial."""
    cpf = re.sub(r"\D", "", cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True


@app.get("/validar-cpf/sucesso/{cpf}")
async def validar_sucesso(cpf: str):
    """Resposta imediata e bem-sucedida."""
    valido = cpf_valido(cpf)
    return {
        "cpf": cpf,
        "valido": valido,
        "modo": "sucesso",
        "mensagem": "CPF válido." if valido else "CPF inválido.",
    }


@app.get("/validar-cpf/lento/{cpf}")
async def validar_lento(cpf: str):
    """Simula lentidão com delay de 10 segundos."""
    await asyncio.sleep(10)
    valido = cpf_valido(cpf)
    return {
        "cpf": cpf,
        "valido": valido,
        "modo": "lento",
        "mensagem": "Resposta com atraso.",
    }


@app.get("/validar-cpf/falha/{cpf}")
async def validar_falha(cpf: str):
    """Simula falha retornando erro 500."""
    raise Exception("Serviço externo indisponível!")


@app.get("/health")
async def health():
    return {"status": "ok", "servico": "validador-cpf"}
