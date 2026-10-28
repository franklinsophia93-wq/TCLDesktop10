#!/usr/bin/env python3
"""NegocioFacil 0.4: identidade AdMob real, banner seguro em DEMONSTRACAO."""
from pathlib import Path
import sys

APP_ID = "ca-app-pub-3687557234604048~3806971268"
BANNER_ID = "ca-app-pub-3687557234604048/1287077145"
DEMO_BANNER = "ca-app-pub-3940256099942544/6300978111"
DEMO_APP = "ca-app-pub-3940256099942544~3347511713"

def replace_one(text, before, after, purpose):
    n = text.count(before)
    if n != 1:
        raise RuntimeError(f"{purpose}: esperado uma ocorrencia, encontradas {n}")
    return text.replace(before, after, 1)

def main(path):
    base = Path(path)
    manifest = base / "android/app/src/main/AndroidManifest.xml"
    java = base / "android/app/src/main/java/br/com/negociofacil/app/MainActivity.java"
    gradle = base / "android/app/build.gradle"
    m = manifest.read_text(encoding="utf-8")
    j = java.read_text(encoding="utf-8")
    g = gradle.read_text(encoding="utf-8")
    m = replace_one(m, DEMO_APP, APP_ID, "App AdMob associado ao proprietario")
    field = '    private static final String TEST_BANNER_ID = "' + DEMO_BANNER + '";'
    # Mantem a unidade TESTE no APK, para que nenhum dispositivo de homologacao
    # solicite acidentalmente anuncios reais ou gere trafego invalido.
    addition = (
        '    private static final String ADMOB_PRODUCTION_BANNER_ID = "' + BANNER_ID + '";\n'
        '    private static final boolean ADS_RELEASE_AUTHORIZED = false;\n'
        '    private static final String TEST_BANNER_ID = "' + DEMO_BANNER + '";'
    )
    j = replace_one(j, field, addition, "ID do banner e bloqueio de producao")
    # O teste usa exclusivamente o banner de demonstracao. O bloqueio esta
    # duplicado no fluxo de criacao para impedir regressao acidental.
    j = replace_one(j,
        "                banner.setAdUnitId(TEST_BANNER_ID);",
        '                banner.setAdUnitId(ADS_RELEASE_AUTHORIZED ? ADMOB_PRODUCTION_BANNER_ID : TEST_BANNER_ID);',
        "selecao segura entre demo e producao")
    g = replace_one(g, "versionCode 3", "versionCode 4", "versionCode Android")
    g = replace_one(g, "versionName '0.3.0-documentos-admob-teste'",
                       "versionName '0.4.0-admob-identificado-teste'", "versionName")
    manifest.write_text(m, encoding="utf-8")
    java.write_text(j, encoding="utf-8")
    gradle.write_text(g, encoding="utf-8")
    verify(base)

def verify(root):
    manifest = (root/"android/app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    j = (root/"android/app/src/main/java/br/com/negociofacil/app/MainActivity.java").read_text(encoding="utf-8")
    g = (root/"android/app/build.gradle").read_text(encoding="utf-8")
    assert APP_ID in manifest
    assert DEMO_APP not in manifest
    assert BANNER_ID in j
    assert "ADS_RELEASE_AUTHORIZED = false;" in j
    assert "TEST_BANNER_ID = \"" + DEMO_BANNER + "\";" in j
    assert "versionCode 4" in g
    assert "applicationId 'br.com.negociofacil.app'" in g
    print("v0.4 pronto: ID AdMob correto, unidade real cadastrada, banners AINDA EM TESTE.", flush=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: upgrade_v04_admob.py /caminho/para/fonte")
    main(sys.argv[1])
