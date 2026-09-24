# Bot de Tickets + Registro

Bot em Python (discord.py) com:
- Painel de ticket com dois botões: **Comprar** (verde, 💰) e **Dúvida** (azul, ❓)
- Log automático de abertura e fechamento de tickets
- Painel de auto-registro: pede o nome da pessoa e atribui um cargo (definido no `.env`)

## Instalação

1. Instale o Python 3.10+ (se ainda não tiver).
2. Nesta pasta, abra um terminal e instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Abra o arquivo `.env` e preencha:
   - `TOKEN` — token do bot no Discord Developer Portal
   - `STAFF_ROLE_ID` — ID do cargo de staff (opcional, mas recomendado)
   - `TICKET_CATEGORY_ID` — ID da categoria onde os tickets serão criados (opcional)
   - `LOG_CHANNEL_ID` — ID do canal de logs
   - `REGISTER_ROLE_ID` — ID do cargo dado ao se registrar

## Como pegar os IDs

No Discord, ative o **Modo Desenvolvedor** (Configurações → Avançado), depois
clique com o botão direito no cargo/canal/categoria e escolha **Copiar ID**.

## Rodando o bot

```
python bot.py
```

## Comandos (uso de administrador)

- `!painel` — envia o painel de tickets (Comprar / Dúvida)
- `!registro` — envia o painel de auto-registro

Os botões usam `custom_id` fixo, então continuam funcionando mesmo depois de
reiniciar o bot — não precisa reenviar os painéis toda vez.
