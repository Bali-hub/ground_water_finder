# build_deploy.ps1 - Script complet de build et déploiement
Write-Host "🚀 GROUND WATER FINDER - DEPLOYMENT SCRIPT" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Vérifications
function Check-Requirements {
    Write-Host "`n🔍 VÉRIFICATION DES PRÉREQUIS..." -ForegroundColor Yellow
    
    $checks = @{
        "Dockerfile" = Test-Path "Dockerfile"
        "requirements.txt" = Test-Path "requirements.txt"
        "app.py" = Test-Path "app.py"
        "render.yaml" = Test-Path "render.yaml"
        ".dockerignore" = Test-Path ".dockerignore"
    }
    
    foreach ($check in $checks.GetEnumerator()) {
        if ($check.Value) {
            Write-Host "  ✅ $($check.Key)" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $($check.Key) MANQUANT" -ForegroundColor Red
            return $false
        }
    }
    
    # Vérifier Docker (optionnel pour test local)
    try {
        docker --version 2>&1 | Out-Null
        Write-Host "  ✅ Docker disponible" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Docker non installé (test local seulement)" -ForegroundColor Yellow
    }
    
    return $true
}

# Test local Docker
function Test-LocalDocker {
    Write-Host "`n🧪 TEST LOCAL DOCKER..." -ForegroundColor Yellow
    
    try {
        # Build
        Write-Host "  🔨 Building Docker image..." -ForegroundColor Gray
        docker build -t ground-water-finder-test .
        
        # Run
        Write-Host "  🚀 Lancement du container test..." -ForegroundColor Gray
        $containerId = docker run -d -p 8501:8501 --name gwt-test ground-water-finder-test
        
        # Attendre
        Write-Host "  ⏳ Attente du démarrage (30s)..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        
        # Test health check
        $health = Invoke-RestMethod -Uri "http://localhost:8501/_stcore/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($health) {
            Write-Host "  ✅ Application fonctionnelle!" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Health check échoué" -ForegroundColor Yellow
        }
        
        # Cleanup
        Write-Host "  🧹 Nettoyage..." -ForegroundColor Gray
        docker stop $containerId 2>$null
        docker rm $containerId 2>$null
        
        return $true
    } catch {
        Write-Host "  ❌ Erreur test Docker: $_" -ForegroundColor Red
        return $false
    }
}

# Validation des fichiers
function Validate-Files {
    Write-Host "`n📄 VALIDATION DES FICHIERS..." -ForegroundColor Yellow
    
    # Dockerfile
    $dockerContent = Get-Content Dockerfile -Raw
    if ($dockerContent -notmatch "FROM python:3.10") {
        Write-Host "  ⚠️  Dockerfile: Python 3.10 recommandé" -ForegroundColor Yellow
    }
    
    if ($dockerContent -notmatch "playwright install chromium") {
        Write-Host "  ❌ Dockerfile: Playwright non configuré" -ForegroundColor Red
        return $false
    }
    
    # requirements.txt
    $reqs = Get-Content requirements.txt
    if ($reqs -notmatch "streamlit") {
        Write-Host "  ❌ requirements.txt: Streamlit manquant" -ForegroundColor Red
        return $false
    }
    
    if ($reqs -notmatch "playwright") {
        Write-Host "  ⚠️  requirements.txt: Playwright manquant" -ForegroundColor Yellow
    }
    
    # render.yaml
    $render = Get-Content render.yaml -Raw
    if ($render -notmatch "env: docker") {
        Write-Host "  ❌ render.yaml: 'env: docker' manquant" -ForegroundColor Red
        return $false
    }
    
    Write-Host "  ✅ Tous les fichiers sont valides" -ForegroundColor Green
    return $true
}

# Déploiement instructions
function Show-DeployInstructions {
    Write-Host "`n🚀 INSTRUCTIONS DE DÉPLOIEMENT RENDER:" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    Write-Host "`n1. 📁 Poussez sur GitHub:" -ForegroundColor White
    Write-Host "   git add ." -ForegroundColor Gray
    Write-Host "   git commit -m 'Deploy Ground Water Finder'" -ForegroundColor Gray
    Write-Host "   git push origin main" -ForegroundColor Gray
    
    Write-Host "`n2. 🌐 Déployez sur Render:" -ForegroundColor White
    Write-Host "   a. Allez sur https://render.com" -ForegroundColor Gray
    Write-Host "   b. 'New +' → 'Web Service'" -ForegroundColor Gray
    Write-Host "   c. Connectez votre repo GitHub" -ForegroundColor Gray
    Write-Host "   d. Render détectera automatiquement render.yaml" -ForegroundColor Gray
    Write-Host "   e. Configurez le plan 'starter' ($7/mois)" -ForegroundColor Gray
    Write-Host "   f. Déployez!" -ForegroundColor Gray
    
    Write-Host "`n3. ✅ Vérification:" -ForegroundColor White
    Write-Host "   - Build: 10-20 minutes" -ForegroundColor Gray
    Write-Host "   - URL: https://ground-water-finder.onrender.com" -ForegroundColor Gray
    Write-Host "   - Logs: Dashboard Render → Logs" -ForegroundColor Gray
    
    Write-Host "`n💰 COÛT ESTIMÉ: $7/mois (Starter plan)" -ForegroundColor Green
}

# Main execution
Write-Host "`n📍 Répertoire: $(Get-Location)" -ForegroundColor Gray

if (-not (Check-Requirements)) {
    Write-Host "❌ Prérequis non satisfaits" -ForegroundColor Red
    exit 1
}

if (-not (Validate-Files)) {
    Write-Host "❌ Validation des fichiers échouée" -ForegroundColor Red
    exit 1
}

# Demander test local
$testLocal = Read-Host "`n🧪 Voulez-vous tester localement avec Docker? (O/n)"
if ($testLocal -eq "" -or $testLocal -eq "O" -or $testLocal -eq "o") {
    Test-LocalDocker
}

Show-DeployInstructions

Write-Host "`n🎉 PRÊT POUR LE DÉPLOIEMENT !" -ForegroundColor Green -BackgroundColor DarkBlue
Write-Host "=================================" -ForegroundColor Green