#!/usr/bin/env python3
"""NegocioFacil v0.5: compartilhamento nativo Android via ACTION_SEND."""
from pathlib import Path
import sys

def replace_one(source, needle, replacement, what):
    total = source.count(needle)
    if total != 1:
        raise RuntimeError(f'{what}: esperado 1, encontrado {total}')
    return source.replace(needle, replacement, 1)

def patch(root):
    base = Path(root)
    js_file = base / 'web/app.js'
    java_file = base / 'android/app/src/main/java/br/com/negociofacil/app/MainActivity.java'
    gradle_file = base / 'android/app/build.gradle'
    js = js_file.read_text(encoding='utf-8')
    java = java_file.read_text(encoding='utf-8')
    gradle = gradle_file.read_text(encoding='utf-8')

    js = replace_one(js,
        '    if(navigator.share)navigator.share({title:x.title,text:msg}).catch(()=>{});',
        "    if(bridge() && typeof bridge().shareText==='function')bridge().shareText(x.title,msg);\n"
        '    else if(navigator.share)navigator.share({title:x.title,text:msg}).catch(()=>{});',
        'Botao compartilhar campanhas')
    js = replace_one(js,
        "if(navigator.share)navigator.share({title:'Orçamento',text:msg}).catch(()=>{});else if(navigator.clipboard",
        "if(bridge() && typeof bridge().shareText==='function')bridge().shareText('Orçamento',msg);else if(navigator.share)navigator.share({title:'Orçamento',text:msg}).catch(()=>{});else if(navigator.clipboard",
        'Compartilhar orcamentos')
    java = replace_one(java,
        '    private final class LocalActions {',
        '''    /** Compartilhamento nativo: a pessoa escolhe o aplicativo de destino. */
    private void openAndroidSharesheet(String title, String text) {
        if (text == null || text.trim().isEmpty() || text.length() > 12000) {
            show("Mensagem vazia ou muito longa para compartilhar.");
            return;
        }
        runOnUiThread(() -> {
            try {
                Intent share = new Intent(Intent.ACTION_SEND);
                share.setType("text/plain");
                share.putExtra(Intent.EXTRA_TEXT, text);
                String subject = title == null ? "NegócioFácil" : title.trim();
                if (subject.length() > 100) subject = subject.substring(0, 100);
                share.putExtra(Intent.EXTRA_SUBJECT, subject);
                startActivity(Intent.createChooser(share, "Compartilhar pelo NegócioFácil"));
            } catch (ActivityNotFoundException e) {
                show("Nenhum aplicativo disponível para compartilhar.");
            } catch (Exception e) {
                show("Não foi possível abrir o menu de compartilhamento.");
            }
        });
    }

    private final class LocalActions {
        @JavascriptInterface public void shareText(String title, String text) {
            openAndroidSharesheet(title, text);
        }
''',
        'Ponte Javascript para ACTION_SEND')
    gradle = replace_one(gradle, 'versionCode 4', 'versionCode 5', 'Versao Android')
    gradle = replace_one(gradle,
        "versionName '0.4.0-admob-identificado-teste'",
        "versionName '0.5.0-compartilhamento-teste'", 'Nome da versao')

    js_file.write_text(js, encoding='utf-8')
    java_file.write_text(java, encoding='utf-8')
    gradle_file.write_text(gradle, encoding='utf-8')
    print('NegocioFacil 0.5: compartilhamento nativo para Marketing e Orcamentos, versionCode 5.')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('Uso: upgrade_v05_sharing.py /fonte')
    patch(sys.argv[1])
