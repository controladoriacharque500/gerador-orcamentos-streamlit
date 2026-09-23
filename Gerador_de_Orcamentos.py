import streamlit as pd_st
import pandas as pd
from fpdf import FPDF
import tempfile
from datetime import datetime
import gspread

# Configuração da Página
pd_st.set_page_config(page_title="Gerador de Orçamentos Rápido", page_icon="📄", layout="centered")

pd_st.title("📄 Gerador de Orçamentos Profissional")
pd_st.markdown("Crie orçamentos limpos e rápidos para enviar aos seus clientes pelo WhatsApp.")

# Inicializar o session_state para persistência
if "prestador" not in pd_st.session_state:
    pd_st.session_state.prestador = {
        "nome": "João Serviços",
        "tel": "(21) 99999-9999",
        "email": "joao@email.com",
        "ramo": "Obras e Reformas",
        "ramo_outro": ""
    }

if "cliente" not in pd_st.session_state:
    pd_st.session_state.cliente = {
        "nome": "Maria da Silva",
        "tel": "(21) 98888-8888"
    }

if "condicoes" not in pd_st.session_state:
    pd_st.session_state.condicoes = {
        "validade": "7 dias",
        "pagamento": "Pix ou Dinheiro (50% de entrada)"
    }

if "itens" not in pd_st.session_state:
    pd_st.session_state.itens = [{"descricao": "Serviço de Exemplo", "qtd": 1, "valor": 150.0}]

# --- 1. DADOS DO PRESTADOR ---
pd_st.header("1. Seus Dados (Prestador)")
col1, col2 = pd_st.columns(2)
with col1:
    pd_st.session_state.prestador["nome"] = pd_st.text_input("Seu Nome / Nome da Empresa", value=pd_st.session_state.prestador["nome"])
    pd_st.session_state.prestador["tel"] = pd_st.text_input("Seu Telefone / WhatsApp", value=pd_st.session_state.prestador["tel"])
with col2:
    pd_st.session_state.prestador["email"] = pd_st.text_input("Seu E-mail", value=pd_st.session_state.prestador["email"])
    
ramos_disponiveis = [
    "Obras e Reformas", 
    "Elétrica / Instalações", 
    "Confeitaria / Alimentação", 
    "Serviços Gerais / Manutenção", 
    "Beleza e Estética", 
    "Outros"
]

ramo_atual = pd_st.session_state.prestador["ramo"]
idx_ramo = ramos_disponiveis.index(ramo_atual) if ramo_atual in ramos_disponiveis else (5 if ramo_atual else 0)

escolha_ramo = pd_st.selectbox(
    "Sua Profissão / Ramo de Atuação", 
    options=ramos_disponiveis, 
    index=idx_ramo
)

if escolha_ramo == "Outros":
    pd_st.session_state.prestador["ramo_outro"] = pd_st.text_input(
        "Digite qual é a sua profissão/ramo:", 
        value=pd_st.session_state.prestador.get("ramo_outro", "")
    )
    pd_st.session_state.prestador["ramo"] = pd_st.session_state.prestador["ramo_outro"] if pd_st.session_state.prestador["ramo_outro"] else "Outros"
else:
    pd_st.session_state.prestador["ramo"] = escolha_ramo

pd_st.divider()

# --- 2. DADOS DO CLIENTE ---
pd_st.header("2. Dados do Cliente")
col3, col4 = pd_st.columns(2)
with col3:
    pd_st.session_state.cliente["nome"] = pd_st.text_input("Nome do Cliente", value=pd_st.session_state.cliente["nome"])
with col4:
    pd_st.session_state.cliente["tel"] = pd_st.text_input("Telefone do Cliente", value=pd_st.session_state.cliente["tel"])

pd_st.divider()

# --- 3. CONDIÇÕES DO ORÇAMENTO ---
pd_st.header("3. Condições Comerciais")
col5, col6 = pd_st.columns(2)
with col5:
    pd_st.session_state.condicoes["validade"] = pd_st.text_input("Validade do Orçamento", value=pd_st.session_state.condicoes["validade"])
with col6:
    pd_st.session_state.condicoes["pagamento"] = pd_st.text_input("Forma de Pagamento", value=pd_st.session_state.condicoes["pagamento"])

pd_st.divider()

# --- 4. PRODUTOS / SERVIÇOS ---
pd_st.header("4. Produtos / Serviços")

with pd_st.form("form_item", clear_on_submit=True):
    c1, c2, c3 = pd_st.columns([3, 1, 1])
    desc = c1.text_input("Descrição do Item/Serviço")
    qtd = c2.number_input("Qtd", min_value=1, value=1)
    valor = c3.number_input("Valor Unitário (R$)", min_value=0.0, value=0.0, format="%.2f")
    
    adicionar = pd_st.form_submit_button("Adicionar Item")
    if adicionar and desc:
        pd_st.session_state.itens.append({"descricao": desc, "qtd": qtd, "valor": valor})
        pd_st.rerun()

if pd_st.session_state.itens:
    df_itens = pd.DataFrame(pd_st.session_state.itens)
    df_itens["Total Parcial"] = df_itens["qtd"] * df_itens["valor"]
    
    pd_st.write("Itens adicionados:")
    pd_st.dataframe(df_itens, use_container_width=True)
    
    if pd_st.button("Limpar Todos os Itens"):
        pd_st.session_state.itens = []
        pd_st.rerun()
        
    total_geral = df_itens["Total Parcial"].sum()
    pd_st.subheader(f"Valor Total do Orçamento: R$ {total_geral:.2f}")

# --- 5. INTEGRAÇÃO COM GOOGLE SHEETS (DIRETA) ---
def conectar_google_drive():
    try:
        # Lê a partir da estrutura [connections.gsheets] configurada nos Secrets
        if "connections" in pd_st.secrets and "gsheets" in pd_st.secrets["connections"]:
            secrets_dict = dict(pd_st.secrets["connections"]["gsheets"])
            if "-----BEGIN PRIVATE KEY-----" not in secrets_dict["private_key"]:
                pk = secrets_dict["private_key"].replace('\\n', '\n')
                secrets_dict["private_key"] = pk
            return gspread.service_account_from_dict(secrets_dict)
        elif "gcp_service_account" in pd_st.secrets: # Compatibilidade caso use o outro nome
            secrets_dict = dict(pd_st.secrets["gcp_service_account"])
            if "-----BEGIN PRIVATE KEY-----" not in secrets_dict["private_key"]:
                pk = secrets_dict["private_key"].replace('\\n', '\n')
                secrets_dict["private_key"] = pk
            return gspread.service_account_from_dict(secrets_dict)
        else:
            pd_st.error("As credenciais do Google Sheets não foram encontradas nos Secrets do Streamlit.")
            return None
    except Exception as e:
        pd_st.error(fog=f"Erro na conexão com Google Drive: {e}")
        return None

def salvar_lead_na_planilha(prestador, cliente, condicoes):
    try:
        gc = conectar_google_drive()
        if gc:
            sh = gc.open("Leads_Gerador_Orcamentos") 
            worksheet = sh.worksheet("Leads")
            
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            linha = [
                data_atual,
                prestador.get("nome"),
                prestador.get("email"),
                prestador.get("tel"),
                cliente.get("nome"),
                condicoes.get("validade"),
                condicoes.get("pagamento"),
                prestador.get("ramo")
            ]
            worksheet.append_row(linha)
            return True
    except Exception as e:
        pd_st.error(f"Erro ao salvar na planilha: {e}")
        return False

# --- 6. FUNÇÃO DE GERAÇÃO DE PDF ---
def gerar_pdf(prestador, cliente, condicoes, itens, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="ORÇAMENTO DE SERVIÇOS", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=f"Emitido por: {prestador['nome']} | Tel: {prestador['tel']}", ln=True, align="C")
    pdf.cell(200, 5, txt=f"E-mail: {prestador['email']} | Ramo: {prestador['ramo']}", ln=True, align="C")
    pdf.ln(8)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(200, 6, txt="Dados do Cliente:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=f"Cliente: {cliente['nome']} (Tel: {cliente['tel']})", ln=True)
    pdf.ln(4)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(200, 6, txt="Condições:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 5, txt=f"Validade da Proposta: {condicoes['validade']}", ln=True)
    pdf.cell(200, 5, txt=f"Forma de Pagamento: {condicoes['pagamento']}", ln=True)
    pdf.ln(8)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 7, "Descrição", 1)
    pdf.cell(30, 7, "Qtd", 1, align="C")
    pdf.cell(30, 7, "Preço Unit.", 1, align="C")
    pdf.cell(30, 7, "Total", 1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for item in itens:
        t_parcial = item["qtd"] * item["valor"]
        pdf.cell(100, 6, str(item["descricao"]), 1)
        pdf.cell(30, 6, str(item["qtd"]), 1, align="C")
        pdf.cell(30, 6, f"R$ {item['valor']:.2f}", 1, align="C")
        pdf.cell(30, 6, f"R$ {t_parcial:.2f}", 1, align="C")
        pdf.ln()
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(160, 10, "VALOR TOTAL:", 0, 0, "R")
    pdf.cell(30, 10, f"R$ {total:.2f}", 1, 1, "C")
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# --- 7. BOTÃO DE GERAR PDF ---
if pd_st.session_state.itens:
    if pd_st.button("Gerar PDF do Orçamento 🚀", type="primary"):
        with pd_st.spinner("Registrando dados e gerando PDF..."):
            # Salva de forma síncrona para garantir o envio correto
            sucesso_planilha = salvar_lead_na_planilha(
                pd_st.session_state.prestador,
                pd_st.session_state.cliente,
                pd_st.session_state.condicoes
            )
            
            pdf_path = gerar_pdf(
                pd_st.session_state.prestador,
                pd_st.session_state.cliente,
                pd_st.session_state.condicoes,
                pd_st.session_state.itens,
                total_geral
            )
        
        if sucesso_planilha:
            pd_st.success("Dados registrados na planilha e orçamento gerado com sucesso!")
        else:
            pd_st.warning("O PDF foi gerado, mas houve um alerta ao salvar na planilha. Verifique o painel.")
            
        with open(pdf_path, "rb") as f:
            pd_st.download_button(
                label="📥 Baixar PDF Pronto",
                data=f,
                file_name=f"orcamento_cliente_{nome_cliente}.pdf",
                mime="application/pdf"
            )
