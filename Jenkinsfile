// ==============================================================================
// Nexvion E-Commerce Workload — Enterprise CI/CD Pipeline (Phase 2 Hardened)
// Target Agent: Linux Environment (Ubuntu / Alpine / Amazon Linux)
// Security Scanning: GitLeaks v8.28.0 & Trivy 0.60.0
// Deployment Target: Staging Docker Compose (K8s replacement in Phase 4)
// ==============================================================================

pipeline {
    agent {
        node {
            label 'linux'
        }
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        ansiColor('xterm')
    }

    parameters {
        choice(name: 'REGISTRY_TYPE', choices: ['LOCAL_ONLY', 'AWS_ECR', 'DOCKER_HUB'], description: 'Target Container Registry Type (Safe Default: LOCAL_ONLY)')
        string(name: 'REGISTRY_URL', defaultValue: '123456789012.dkr.ecr.ap-south-1.amazonaws.com', description: 'Container Registry Endpoint/URI')
        booleanParam(name: 'PUSH_TO_REGISTRY', defaultValue: false, description: 'Push built Docker images to registry (Default: false until real ECR configured)')
        booleanParam(name: 'DEPLOY_STAGING', defaultValue: true, description: 'Deploy stack to staging environment after scanning')
        string(name: 'TRIVY_SEVERITY', defaultValue: 'HIGH,CRITICAL', description: 'Security scan severity failure threshold')
    }

    environment {
        APP_NAME                 = 'nexvion-web'
        REGISTRY_CREDENTIALS_ID   = 'ecr-credentials' // Temporary Phase 2 credential fallback; Phase 3/4 uses IAM Roles (IRSA)
        AWS_REGION               = 'ap-south-1'
        HEALTH_CHECK_URL         = 'http://localhost:8080/healthz'
        ROOT_CHECK_URL           = 'http://localhost:8080/'
        
        // Pinned Scanner Versions
        GITLEAKS_IMAGE           = 'zricethezav/gitleaks:v8.28.0'
        TRIVY_IMAGE              = 'aquasec/trivy:0.60.0'
        
        // Primary Immutable Tag (Git SHA) & Secondary Tags
        GIT_COMMIT_SHORT         = ""
        IMAGE_TAG_COMMIT         = ":"  // Primary Immutable Artifact
        IMAGE_TAG_BUILD          = ":"      // Secondary Tag
        IMAGE_TAG_LATEST         = ":latest"               // Utility Tag
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    echo "=== STAGE 1: CHECKOUT ==="
                    echo "Workload: Nexvion E-Commerce Frontend"
                    echo "Target Runner OS: Linux Agent"
                    echo "Build Number: "
                    echo "Git Commit (Primary Immutable SHA): "
                }
            }
        }

        stage('Validate') {
            steps {
                script {
                    echo "=== STAGE 2: VALIDATION ==="
                    echo "Verifying existence of required application static workload files..."

                    def requiredFiles = [
                        'index.html', 'products.html', 'payment.html',
                        'style.css', 'products.css', 'payment.css',
                        'script.js', 'payment.js', 'logo.png',
                        'nginx.conf', 'Dockerfile', 'docker-compose.yml', '.gitleaks.toml'
                    ]

                    requiredFiles.each { filename ->
                        if (!fileExists(filename)) {
                            error "VALIDATION FAILURE: Required workload file '' is missing!"
                        }
                        echo "  [OK]  exists"
                    }

                    echo "Validating JavaScript syntax using Node.js..."
                    sh(script: 'node -c script.js', label: 'Validate script.js')
                    sh(script: 'node -c payment.js', label: 'Validate payment.js')
                    echo "  [OK] JavaScript syntax verified cleanly."

                    echo "Validating Docker Compose configuration..."
                    sh(script: 'docker compose config', label: 'Validate docker-compose.yml')
                    echo "  [OK] docker-compose.yml syntax valid."
                }
            }
        }

        stage('Secret Scan') {
            steps {
                script {
                    echo "=== STAGE 3: DEVSECOPS SECRET SCANNING (GITLEAKS) ==="
                    echo "Scanner Version: "
                    echo "Policy: Strict Repository Scan (No broad doc exclusions)"

                    def status = sh(
                        script: """
                            docker run --rm -v "\:/path" \
                                 detect \
                                --source="/path" \
                                -c="/path/.gitleaks.toml" \
                                --no-git -v
                        """,
                        returnStatus: true,
                        label: 'GitLeaks Scan Execution'
                    )

                    if (status != 0) {
                        error "SECURITY GATE FAILURE: GitLeaks detected hardcoded credentials or API keys!"
                    } else {
                        echo "  [PASS] GitLeaks secret scan completed — 0 leaks detected."
                    }
                }
            }
        }

        stage('Docker Build') {
            steps {
                script {
                    echo "=== STAGE 4: DOCKER IMAGE BUILD ==="
                    echo "Primary Immutable Image Tag: "
                    echo "Secondary Tags: , "

                    sh(
                        script: """
                            docker build \
                                -t  \
                                -t  \
                                -t  \
                                .
                        """,
                        label: 'Docker Image Build'
                    )
                    echo "  [OK] Docker image built successfully."
                }
            }
        }

        stage('Image Scan') {
            steps {
                script {
                    echo "=== STAGE 5: DEVSECOPS CONTAINER VULNERABILITY SCAN (TRIVY) ==="
                    echo "Scanner Version: "
                    echo "Target Image: "
                    echo "Severity Threshold: "

                    // Print vulnerability summary table
                    sh(
                        script: """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                 image \
                                --severity  \
                                --exit-code 0 \
                                
                        """,
                        label: 'Trivy Scan Report'
                    )

                    // Enforce hard security gate failure if HIGH or CRITICAL findings exist
                    def scanStatus = sh(
                        script: """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                 image \
                                --severity  \
                                --exit-code 1 \
                                
                        """,
                        returnStatus: true,
                        label: 'Trivy Security Gate Check'
                    )

                    if (scanStatus != 0) {
                        error "SECURITY GATE FAILURE: Trivy detected HIGH or CRITICAL vulnerabilities exceeding policy limit!"
                    } else {
                        echo "  [PASS] Trivy container scan PASSED — 0 High/Critical vulnerabilities found."
                    }
                }
            }
        }

        stage('Registry Push') {
            when {
                expression { return params.PUSH_TO_REGISTRY && params.REGISTRY_TYPE != 'LOCAL_ONLY' }
            }
            steps {
                script {
                    echo "=== STAGE 6: CONTAINER REGISTRY PUSH ==="
                    echo "Target Registry:  ()"

                    if (params.REGISTRY_TYPE == 'AWS_ECR') {
                        echo "Authentication Strategy: Phase 2 Credential Fallback (Phase 3/4 uses IAM Roles / IRSA)"
                        withCredentials([usernamePassword(
                            credentialsId: env.REGISTRY_CREDENTIALS_ID,
                            usernameVariable: 'AWS_ACCESS_KEY_ID',
                            passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                        )]) {
                            sh(script: """
                                aws ecr get-login-password --region  | \
                                docker login --username AWS --password-stdin 
                            """, label: 'AWS ECR Login')

                            def remoteTagCommit = "/"
                            def remoteTagBuild  = "/"
                            def remoteTagLatest = "/"

                            sh(script: "docker tag  ", label: 'Tag ECR Primary SHA')
                            sh(script: "docker tag  ", label: 'Tag ECR Build Number')
                            sh(script: "docker tag  ", label: 'Tag ECR Latest')

                            echo "Pushing Primary Immutable SHA Tag ()..."
                            sh(script: "docker push ", label: 'Push Primary ECR Tag')
                            sh(script: "docker push ", label: 'Push Secondary ECR Tag')
                            sh(script: "docker push ", label: 'Push Latest Tag')

                            echo "  [OK] Primary immutable artifact pushed successfully to AWS ECR."
                        }
                    } else if (params.REGISTRY_TYPE == 'DOCKER_HUB') {
                        withCredentials([usernamePassword(
                            credentialsId: env.REGISTRY_CREDENTIALS_ID,
                            usernameVariable: 'DOCKER_USER',
                            passwordVariable: 'DOCKER_PASS'
                        )]) {
                            sh(script: 'echo "" | docker login -u "" --password-stdin', label: 'Docker Hub Login')
                            def remoteTag = "/"
                            sh(script: "docker tag  ", label: 'Tag Remote')
                            sh(script: "docker push ", label: 'Push Docker Hub')
                            echo "  [OK] Image pushed successfully to Docker Hub."
                        }
                    }
                }
            }
        }

        stage('Deployment') {
            when {
                expression { return params.DEPLOY_STAGING }
            }
            steps {
                script {
                    echo "=== STAGE 7: LOCAL STAGING DEPLOYMENT ==="
                    echo "Note: Docker Compose is used for Phase 2 staging; Phase 4 will replace this with Kubernetes (Helm/EKS)."
                    
                    sh(
                        script: 'docker compose up -d --force-recreate',
                        label: 'Deploy Staging Stack'
                    )

                    echo "  [OK] Staging container stack deployed successfully."
                    sleep(time: 5, unit: 'SECONDS')
                }
            }
        }

        stage('Health Check') {
            when {
                expression { return params.DEPLOY_STAGING }
            }
            steps {
                script {
                    echo "=== STAGE 8: POST-DEPLOYMENT HEALTH VERIFICATION ==="
                    echo "Verifying HTTP GET /healthz..."

                    def healthStatus = sh(
                        script: "curl -s -o /dev/null -w '%{http_code}' ",
                        returnStdout: true,
                        label: 'Check /healthz HTTP status'
                    ).trim()

                    echo "  /healthz Status Code: "
                    if (healthStatus != '200') {
                        error "HEALTH CHECK FAILURE:  returned HTTP  (Expected 200)!"
                    }

                    echo "Verifying Root Web Workload /..."
                    def rootStatus = sh(
                        script: "curl -s -o /dev/null -w '%{http_code}' ",
                        returnStdout: true,
                        label: 'Check / HTTP status'
                    ).trim()

                    echo "  Root (/) Status Code: "
                    if (rootStatus != '200') {
                        error "HEALTH CHECK FAILURE:  returned HTTP  (Expected 200)!"
                    }

                    echo "  [PASS] ALL STAGING HEALTH CHECKS VERIFIED SUCCESSFULLY (HTTP 200 OK)."
                }
            }
        }
    }

    post {
        always {
            echo "=== PIPELINE EXECUTION COMPLETE ==="
            cleanWs deleteDirs: true, notFailBuild: true
        }
        success {
            echo "SUCCESS: Nexvion CI/CD Pipeline executed cleanly. Primary Tag: "
        }
        failure {
            echo "FAILURE: Pipeline encountered errors. Gathering diagnostic logs..."
            sh(script: 'docker compose logs --tail=50', label: 'Dump Container Logs')
        }
    }
}