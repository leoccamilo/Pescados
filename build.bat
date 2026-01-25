@echo off
echo ========================================
echo  Build - Pescados do Alexandre
echo ========================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale o Python em https://python.org
    pause
    exit /b 1
)

REM Criar diretorio de build
if exist "build_env" rmdir /s /q "build_env"
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [1/4] Criando ambiente virtual...
python -m venv build_env
if errorlevel 1 (
    echo ERRO ao criar venv!
    pause
    exit /b 1
)

echo [2/4] Instalando dependencias...
call build_env\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install flask flask-cors pyinstaller
if errorlevel 1 (
    echo ERRO ao instalar dependencias!
    pause
    exit /b 1
)

echo [3/4] Compilando executavel...
pyinstaller --noconfirm --onefile --windowed ^
    --name "PescadosAlexandre" ^
    --icon "Alexandre.ico" ^
    --add-data "index.html;." ^
    --add-data "manifest.json;." ^
    --add-data "sw.js;." ^
    --add-data "icon-192.png;." ^
    --add-data "icon-512.png;." ^
    --hidden-import "flask" ^
    --hidden-import "flask_cors" ^
    --hidden-import "werkzeug" ^
    --hidden-import "jinja2" ^
    app.py

if errorlevel 1 (
    echo ERRO ao compilar!
    pause
    exit /b 1
)

echo [4/4] Organizando arquivos de distribuicao...

REM Criar pasta de distribuicao
if exist "PescadosAlexandre_Instalador" rmdir /s /q "PescadosAlexandre_Instalador"
mkdir "PescadosAlexandre_Instalador"

REM Copiar executavel
copy "dist\PescadosAlexandre.exe" "PescadosAlexandre_Instalador\"

REM Copiar arquivos necessarios
copy "index.html" "PescadosAlexandre_Instalador\"
copy "manifest.json" "PescadosAlexandre_Instalador\"
copy "sw.js" "PescadosAlexandre_Instalador\"
copy "icon-192.png" "PescadosAlexandre_Instalador\"
copy "icon-512.png" "PescadosAlexandre_Instalador\"
copy "Alexandre.ico" "PescadosAlexandre_Instalador\"

REM Criar arquivo README
echo Pescados do Alexandre - Instrucoes > "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo ===================================== >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo. >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo 1. Copie toda esta pasta para o computador desejado >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo 2. Execute o arquivo PescadosAlexandre.exe >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo 3. O navegador abrira automaticamente >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo 4. Para acessar pelo celular, use o endereco mostrado na janela >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo. >> "PescadosAlexandre_Instalador\LEIA-ME.txt"
echo Mantenha a janela preta aberta enquanto usa o aplicativo. >> "PescadosAlexandre_Instalador\LEIA-ME.txt"

REM Limpar arquivos temporarios
call deactivate
rmdir /s /q "build_env"
rmdir /s /q "build"
rmdir /s /q "dist"
del /q "*.spec" 2>nul

echo.
echo ========================================
echo  BUILD CONCLUIDO COM SUCESSO!
echo ========================================
echo.
echo Pasta de instalacao: PescadosAlexandre_Instalador
echo.
echo Envie esta pasta para o Alexandre.
echo Ele so precisa executar PescadosAlexandre.exe
echo ========================================
echo.
pause
