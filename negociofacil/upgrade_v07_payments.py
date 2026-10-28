#!/usr/bin/env python3
"""NegocioFacil 0.7 - telas de cobrancas Mercado Pago SEM liberar pagamento real."""
from pathlib import Path
import sys

def once(s,a,b,label):
    n=s.count(a)
    if n!=1:raise RuntimeError(f'{label}: esperado 1 encontrado {n}')
    return s.replace(a,b,1)

def main(root):
    root=Path(root)
    js=root/'web/app.js'
    native=root/'android/app/src/main/java/br/com/negociofacil/app/MainActivity.java'
    gradle=root/'android/app/build.gradle'
    a=js.read_text()
    a=once(a,"if(form.id==='cloud-auth-form'||form.id==='cloud-business-form')return cloudSubmit(e);",
        "if(form.id==='cloud-auth-form'||form.id==='cloud-business-form'||form.id==='cloud-sale-form')return cloudSubmit(e);",
        'Formulario de venda')
    a=once(a,"if(action==='cloud-logout'||action==='cloud-connect'||action==='cloud-status')return cloudAction(action,id);",
        "if(action==='cloud-logout'||action==='cloud-connect'||action==='cloud-status'||action==='cloud-sales'||action==='cloud-new-sale'||action==='cloud-charge')return cloudAction(action,id);",
        'Acoes cobrancas')
    n=native.read_text()
    n=once(n,
       '        @JavascriptInterface public String cloudMPStatus(String id){return cloudAccount.mpConnection(id);}',
       '''        @JavascriptInterface public String cloudMPStatus(String id){return cloudAccount.mpConnection(id);}
        @JavascriptInterface public String cloudSales(String id){return cloudAccount.cloudSales(id);}
        @JavascriptInterface public String cloudNewSale(String business,String description,String amount){
            return cloudAccount.cloudNewSale(business,description,amount);
        }
        @JavascriptInterface public String cloudCheckout(String business,String sale){
            return cloudAccount.cloudCheckout(business,sale);
        }''',
       'Ponte Android cobrancas')
    g=gradle.read_text()
    g=once(g,'versionCode 6','versionCode 7','versao')
    g=once(g,"versionName '0.6.0-login-supabase-teste'",
           "versionName '0.7.0-cobrancas-homologacao'",'nome versao')
    js.write_text(a);native.write_text(n);gradle.write_text(g)
    assert 'cloudNewSale' in a and 'cloudNewSale' in n
    print('NegocioFacil v0.7 - registro de vendas, recebimentos online, link de checkout protegido, pagamentos ainda bloqueados')

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Uso: upgrade_v07_payments.py /fontes')
    main(sys.argv[1])
