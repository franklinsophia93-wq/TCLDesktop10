#!/usr/bin/env python3
from pathlib import Path
import sys

def change(content, old, new, desc):
    if content.count(old) != 1:
        raise RuntimeError(f'{desc}: esperado 1, encontrado {content.count(old)}')
    return content.replace(old,new,1)

def upgrade(root):
    root=Path(root)
    app=root/'web/app.js'
    js=app.read_text()
    js=change(js,"  function ad(){return preview==='free'?`<div class=\"ad-card\" aria-label=\"Área publicitária reservada\">▤ &nbsp; Área reservada para publicidade<br>AdMob ainda não ativado</div>`:''}","  function ad(){return preview==='free'&&!bridge()?`<div class=\"ad-card\">Anúncios disponíveis apenas no aplicativo Android</div>`:''}", 'native only ads')
    js=change(js,"${actionTile('▤','Notas fiscais','blue','tax',true)}","${actionTile('▤','Notas fiscais','blue','tax')}",'fiscal menu')
    js=change(js,"tab==='support'&&isPremium()?support():tab==='settings'?settings():more()","tab==='support'&&isPremium()?support():tab==='tax'&&isPremium()?tax():tab==='settings'?settings():more()", 'fiscal route')
    anchor='  function support(){'
    docs = r'''  function tax(){
    const entries=data.sales.filter(s=>s.amount>0).sort((a,b)=>(b.date||'').localeCompare(a.date||''));
    const quotes=data.quotes.filter(q=>q.amount>0).sort((a,b)=>(b.date||'').localeCompare(a.date||''));
    const printRows=(items,kind)=>items.slice(0,30).map(x=>`<div class="list-row"><div class="list-main"><b>${h(kind==='sale'?(x.description||'Venda'):(x.description||'Orçamento'))}</b><small>${dateOnly(x.date)} · ${money(x.amount)} · ${h(nameClient(x.clientId))}</small></div><button class="btn small secondary" data-action="print-document" data-kind="${kind}" data-id="${h(x.id)}">PDF</button></div>`).join('');
    return `${heading('Documentos e notas','Documentos comerciais e emissão pelos canais autorizados.')}
      <div class="warning"><b>Atenção: recibo NÃO é nota fiscal.</b> Os PDFs gerados aqui servem como comprovantes comerciais, sem chave de acesso ou autorização fiscal. Nenhuma nota fiscal é transmitida automaticamente.</div>
      <div class="stack"><div class="card"><b>NFS-e • prestação de serviços</b><p class="tagline">Acesse o Emissor Nacional oficial, entre com sua conta gov.br e emita a nota. A integração direta exige credenciamento fiscal próprio.</p><button class="btn" data-action="official-nfse">Abrir emissor nacional</button></div>
      <div class="card"><b>NF-e • venda de produtos</b><p class="tagline">A emissão de mercadorias depende da SEFAZ e da situação fiscal do negócio. Consulte as orientações oficiais antes de emitir.</p><button class="btn secondary" data-action="official-nfe">Orientações NF-e</button></div>
      <div class="card"><b>Recibos de vendas (PDF)</b><p class="tagline">Gerados no aparelho, com nome do negócio, cliente, valor e data; claramente identificados como NÃO fiscais.</p>${entries.length?`<div class="list">${printRows(entries,'sale')}</div>`:'<p class="tagline">Cadastre uma venda para gerar recibos.</p>'}</div>
      <div class="card"><b>Orçamentos em PDF</b>${quotes.length?`<div class="list">${printRows(quotes,'quote')}</div>`:'<p class="tagline">Cadastre um orçamento para gerar seu documento em PDF.</p>'}</div></div>`;
  }
  function printDocument(kind,id){
    if(!isPremium())return plans();
    const x=(kind==='sale'?data.sales:data.quotes).find(v=>v.id===id);
    if(!x)return notice('Documento não encontrado.');
    if(!bridge()||typeof bridge().printDocument!=='function')return notice('PDF disponível no aplicativo Android instalado.');
    const title=kind==='sale'?'RECIBO DE VENDA':'ORÇAMENTO COMERCIAL';
    const html=`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>body{font:16px Arial;padding:35px;color:#14243a;line-height:1.7}h1{color:#156de2}h2{border-bottom:2px solid #156de2}.warn{padding:12px;border:2px solid #ac2525;background:#fff2f2;color:#8d1616;font-weight:bold}table{width:100%;border-collapse:collapse}td{padding:10px;border-bottom:1px solid #dde3ea}</style></head><body><h1>${h(data.business.name)}</h1><h2>${title}</h2><p class="warn">DOCUMENTO NÃO FISCAL — NÃO SUBSTITUI NOTA FISCAL</p><table><tr><td>Cliente</td><td>${h(nameClient(x.clientId))}</td></tr><tr><td>Descrição</td><td>${h(x.description||'Venda registrada')}</td></tr><tr><td>Data</td><td>${dateOnly(x.date)}</td></tr><tr><td>Valor</td><td><b>${money(x.amount)}</b></td></tr></table><p>Emitido para controle comercial em ${new Date().toLocaleString('pt-BR')}.</p></body></html>`;
    bridge().printDocument(title,html);
    notice('Escolha Salvar como PDF na impressão Android.');
  }
'''
    js=change(js,anchor,docs+anchor,'tax implementation')
    js=change(js,"    if(action==='premium')return premiumFeature(a.dataset.tab||'Funcionalidade avançada');", "    if(action==='official-nfse'){ if(bridge()?.openFiscalPortal)bridge().openFiscalPortal('nfse');else window.open('https://www.gov.br/pt-br/servicos/emitir-nota-fiscal-de-servico-eletronica','_blank','noopener');return; }\n    if(action==='official-nfe'){ if(bridge()?.openFiscalPortal)bridge().openFiscalPortal('nfe');else window.open('https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/servicos-para-mei/nota-fiscal','_blank','noopener');return; }\n    if(action==='print-document')return printDocument(kind,id);\n    if(action==='premium')return premiumFeature(a.dataset.tab||'Funcionalidade avançada');",'fiscal actions')
    js=change(js,"const root=document.getElementById('app');root.innerHTML=header()", "const root=document.getElementById('app');if(bridge()?.setFreePlan)bridge().setFreePlan(!isPremium());root.innerHTML=header()", 'plan synced to native AdMob')
    js=js.replace('Notas fiscais e permissões remotas ainda não estão ativos.', 'Emissão fiscal automática e permissões remotas ainda não estão ativos.')
    app.write_text(js)

    build=root/'android/app/build.gradle'
    s=build.read_text()
    s=change(s,"        versionCode 2\n        versionName '0.2.0-profissionais-teste'", "        versionCode 3\n        versionName '0.3.0-documentos-admob-teste'", 'version bump')
    s=change(s,"    implementation 'androidx.webkit:webkit:1.12.1'", "    implementation 'androidx.webkit:webkit:1.12.1'\n    implementation 'com.google.android.gms:play-services-ads:25.5.0'\n    implementation 'com.google.android.ump:user-messaging-platform:3.2.0'",'ads dependencies')
    build.write_text(s)
    manifest=root/'android/app/src/main/AndroidManifest.xml'
    m=manifest.read_text()
    m=change(m,'    <application','    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="com.google.android.gms.permission.AD_ID" />\n    <application','Internet / Ad ID')
    m=change(m,'        <activity','        <!-- IDs Google de TESTE, nunca geram receita -->\n        <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" android:value="ca-app-pub-3940256099942544~3347511713" />\n        <activity','AdMob test app id')
    manifest.write_text(m)

    java=root/'android/app/src/main/java/br/com/negociofacil/app/MainActivity.java'
    j=java.read_text()
    j=change(j, 'import android.widget.Toast;', '''import android.widget.Toast;
import android.widget.LinearLayout;
import android.widget.FrameLayout;
import android.view.View;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.content.Context;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.AdSize;
import com.google.android.gms.ads.AdView;
import com.google.android.gms.ads.MobileAds;
import com.google.android.ump.ConsentInformation;
import com.google.android.ump.ConsentRequestParameters;
import com.google.android.ump.UserMessagingPlatform;''','native ads imports')
    j=change(j,'    private WebView webView;', '''    private WebView webView;
    private WebView receiptWebView;
    private LinearLayout appLayout;
    private FrameLayout bannerContainer;
    private AdView banner;
    private ConsentInformation consent;
    private boolean consentReady = false;
    private boolean freePlan = true;
    private static final String TEST_BANNER_ID = "ca-app-pub-3940256099942544/6300978111";''', 'ads fields')
    j=change(j,'        setContentView(webView);\n        webView.loadUrl(HOME);', '''        appLayout = new LinearLayout(this);
        appLayout.setOrientation(LinearLayout.VERTICAL);
        appLayout.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1f));
        bannerContainer = new FrameLayout(this);
        bannerContainer.setVisibility(View.GONE);
        appLayout.addView(bannerContainer, new LinearLayout.LayoutParams(-1, -2));
        setContentView(appLayout);
        startAdConsent();
        webView.loadUrl(HOME);''','ad layout')
    point='    private void show(String message) {'
    methods='''    private void startAdConsent() {
        // O consentimento precisa ser verificado a cada início, antes de requisitar anúncios.
        consent = UserMessagingPlatform.getConsentInformation(this);
        ConsentRequestParameters request = new ConsentRequestParameters.Builder().build();
        consent.requestConsentInfoUpdate(this, request,
            () -> UserMessagingPlatform.loadAndShowConsentFormIfRequired(this, error -> {
                consentReady = consent.canRequestAds();
                if (consentReady) {
                    MobileAds.initialize(this, init -> runOnUiThread(this::updateBanner));
                }
                updateBanner();
            }),
            err -> { consentReady = consent.canRequestAds(); updateBanner(); });
    }

    private void updateBanner() {
        runOnUiThread(() -> {
            if (bannerContainer == null) return;
            boolean visible = consentReady && freePlan;
            if (!visible) { bannerContainer.setVisibility(View.GONE); return; }
            if (banner == null) {
                banner = new AdView(this);
                banner.setAdSize(AdSize.BANNER);
                banner.setAdUnitId(TEST_BANNER_ID);
                bannerContainer.addView(banner, new FrameLayout.LayoutParams(-2, -2, android.view.Gravity.CENTER));
                banner.loadAd(new AdRequest.Builder().build());
            }
            bannerContainer.setVisibility(View.VISIBLE);
        });
    }

    private void printCommercialDocument(String title, String html) {
        if (html == null || html.length() > 100000 || !html.contains("DOCUMENTO NÃO FISCAL")) {
            show("Somente documentos comerciais NÃO fiscais são permitidos.");
            return;
        }
        runOnUiThread(() -> {
            if (receiptWebView != null) { receiptWebView.destroy(); receiptWebView = null; }
            receiptWebView = new WebView(this);
            receiptWebView.getSettings().setJavaScriptEnabled(false);
            receiptWebView.setWebViewClient(new WebViewClient() {
                @Override public void onPageFinished(WebView w, String url) {
                    PrintManager manager = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                    if (manager != null) manager.print("NegócioFácil - " + title,
                        w.createPrintDocumentAdapter(title), new PrintAttributes.Builder().build());
                }
            });
            receiptWebView.loadDataWithBaseURL("about:blank", html, "text/html", "UTF-8", null);
        });
    }

'''
    j=change(j,point,methods+point,'native ads / PDF functions')
    j=change(j,'    private final class LocalActions {','''    private final class LocalActions {
        @JavascriptInterface public void setFreePlan(boolean free) {
            freePlan = free;
            updateBanner();
        }

        @JavascriptInterface public void printDocument(String title, String html) {
            printCommercialDocument(title == null ? "Recibo" : title.replaceAll("[^a-zA-ZÀ-ÿ0-9 ]", "").substring(0, Math.min(title.length(), 50)), html);
        }

        @JavascriptInterface public void openFiscalPortal(String type) {
            if ("nfse".equals(type)) runOnUiThread(() -> openExternalUrl("https://www.gov.br/pt-br/servicos/emitir-nota-fiscal-de-servico-eletronica"));
            else if ("nfe".equals(type)) runOnUiThread(() -> openExternalUrl("https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/servicos-para-mei/nota-fiscal"));
        }
''','JS ad + print bridges')
    # Title substring invalid possible after replacing nonlatin; guard by refactoring.
    j=j.replace('title.replaceAll("[^a-zA-ZÀ-ÿ0-9 ]", "").substring(0, Math.min(title.length(), 50))','title.replaceAll("[^a-zA-ZÀ-ÿ0-9 ]", "").substring(0, Math.min(title.replaceAll("[^a-zA-ZÀ-ÿ0-9 ]", "").length(), 50))')
    j=change(j,'        if (webView != null) {','        if (banner != null) { banner.destroy(); banner = null; }\n        if (receiptWebView != null) { receiptWebView.destroy(); receiptWebView = null; }\n        if (webView != null) {','destroy ads / PDF')
    java.write_text(j)
    print('v0.3 aplicado: documentos comerciais PDF, portal oficial NFS-e/NF-e, AdMob TESTE+UMP, versionCode=3')

if __name__ == '__main__': upgrade(Path(sys.argv[1]))