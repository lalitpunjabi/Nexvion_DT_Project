// ==============================================================================
// Nexvion E-Commerce Workload — Enterprise CI/CD Pipeline
//
// Lifecycle Environment Scopes:
//   Phase 2 (Active CI/CD Pipeline):
//     Declarative Jenkinsfile pipeline targeting Linux Agent ('linux')
//     Automated Gates: Checkout ➔ Validate ➔ GitLeaks ➔ Docker Build ➔ Trivy ➔ Staging Deployment ➔ Health Check
//   Phase 3 (Infrastructure as Code & Configuration Management):
//     Terraform infrastructure adoption & Ansible server hardening (CLI validated independently)
//   Phase 4 (Cloud-Native Platform):
//     Amazon EKS + Helm Chart Rolling Updates (Future Production Target)
//
// Target Agent: Linux EC2 Environment (Ubuntu 22.04 LTS)
// Security Scanning: GitLeaks v8.28.0 & Trivy 0.60.0
// Deployment Target: Local Docker Compose (Port 8081:80)
// ==============================================================================


pipeline {

    // --------------------------------------------------------------------------
    // Jenkins must run on a Linux node.
    // Your current EC2 Jenkins node should have the label: linux
    // --------------------------------------------------------------------------

    agent {
        node {
            label 'linux'
        }
    }


    // --------------------------------------------------------------------------
    // Pipeline options
    // --------------------------------------------------------------------------

    options {

        timestamps()

        timeout(
            time: 30,
            unit: 'MINUTES'
        )

        disableConcurrentBuilds()

        ansiColor('xterm')
    }


    // --------------------------------------------------------------------------
    // Parameters
    // --------------------------------------------------------------------------

    parameters {

        choice(
            name: 'REGISTRY_TYPE',
            choices: [
                'LOCAL_ONLY',
                'AWS_ECR',
                'DOCKER_HUB'
            ],
            description:
                'Phase 2 testing should use LOCAL_ONLY.'
        )

        string(
            name: 'REGISTRY_URL',
            defaultValue: '',
            description:
                'Leave empty for LOCAL_ONLY Phase 2 testing.'
        )

        booleanParam(
            name: 'PUSH_TO_REGISTRY',
            defaultValue: false,
            description:
                'Keep false for Phase 2 local EC2 testing.'
        )

        booleanParam(
            name: 'DEPLOY_STAGING',
            defaultValue: true,
            description:
                'Deploy the validated image using Docker Compose.'
        )

        string(
            name: 'TRIVY_SEVERITY',
            defaultValue: 'HIGH,CRITICAL',
            description:
                'Vulnerability severity threshold.'
        )
    }


    // --------------------------------------------------------------------------
    // Static environment variables ONLY.
    //
    // IMPORTANT:
    // Do NOT define GIT_COMMIT_SHORT or IMAGE_TAG_* here.
    // They are calculated directly in the stages.
    // --------------------------------------------------------------------------

    environment {

        APP_NAME = 'nexvion-web'

        AWS_REGION = 'ap-south-1'

        HEALTH_CHECK_URL = 'http://localhost:8081/healthz'

        ROOT_CHECK_URL = 'http://localhost:8081/'

        GITLEAKS_IMAGE =
            'zricethezav/gitleaks:v8.28.0'

        TRIVY_IMAGE =
            'aquasec/trivy:0.60.0'

        NODE_IMAGE =
            'node:22-alpine'

        // Temporary Phase 2 compatibility tag.
        //
        // Current docker-compose.yml uses:
        //
        // image: nexvion-web:v1.0.0
        //
        // The exact SHA image that passes Trivy will be retagged
        // with this value immediately before deployment.

        COMPOSE_IMAGE_TAG =
            'nexvion-web:v1.0.0'
    }


    // ==========================================================================
    // STAGES
    // ==========================================================================

    stages {


        // ======================================================================
        // STAGE 1
        // CHECKOUT
        // ======================================================================

        stage('Checkout') {

            steps {

                checkout scm

                script {

                    echo '============================================================'
                    echo 'STAGE 1: CHECKOUT'
                    echo '============================================================'

                    echo "Workload: Nexvion E-Commerce Frontend"
                    echo "Agent: ${env.NODE_NAME}"
                    echo "Workspace: ${env.WORKSPACE}"
                    echo "Build Number: ${env.BUILD_NUMBER}"

                    // ----------------------------------------------------------
                    // Calculate Git SHA directly.
                    //
                    // We deliberately DO NOT store this in environment {}
                    // because Jenkins environment variables should remain
                    // static for this Phase 2 pipeline.
                    // ----------------------------------------------------------

                    def commitSha = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()

                    if (!commitSha) {

                        error(
                            'CHECKOUT FAILURE: Unable to determine Git commit SHA.'
                        )
                    }

                    echo "Git Commit SHA: ${commitSha}"

                    echo "Primary Image:"
                    echo "${env.APP_NAME}:${commitSha}"

                    echo "Build Image:"
                    echo "${env.APP_NAME}:${env.BUILD_NUMBER}"

                    echo "Latest Image:"
                    echo "${env.APP_NAME}:latest"

                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 2
        // VALIDATION
        // ======================================================================

        stage('Validate') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 2: VALIDATION'
                    echo '============================================================'

                    def requiredFiles = [

                        'index.html',
                        'products.html',
                        'payment.html',

                        'style.css',
                        'products.css',
                        'payment.css',

                        'script.js',
                        'payment.js',

                        'logo.png',

                        'nginx.conf',
                        'Dockerfile',
                        'docker-compose.yml',

                        '.gitleaks.toml'
                    ]


                    // ----------------------------------------------------------
                    // Required files
                    // ----------------------------------------------------------

                    echo 'Checking required project files...'

                    requiredFiles.each { filename ->

                        if (!fileExists(filename)) {

                            error(
                                "VALIDATION FAILURE: " +
                                "Required file '${filename}' is missing."
                            )
                        }

                        echo "[OK] ${filename}"
                    }


                    // ----------------------------------------------------------
                    // JavaScript syntax validation
                    //
                    // Uses Node container so host Node.js is not required.
                    // ----------------------------------------------------------

                    echo 'Validating JavaScript syntax...'

                    sh(
                        script: """
                            docker run --rm \
                                -v "${env.WORKSPACE}:/workspace:ro" \
                                ${env.NODE_IMAGE} \
                                node -c /workspace/script.js
                        """,
                        label: 'Validate script.js'
                    )


                    sh(
                        script: """
                            docker run --rm \
                                -v "${env.WORKSPACE}:/workspace:ro" \
                                ${env.NODE_IMAGE} \
                                node -c /workspace/payment.js
                        """,
                        label: 'Validate payment.js'
                    )


                    echo '[PASS] JavaScript syntax validation completed.'


                    // ----------------------------------------------------------
                    // Docker Compose validation
                    // ----------------------------------------------------------

                    echo 'Validating Docker Compose configuration...'

                    sh(
                        script:
                            'docker compose config',
                        label:
                            'Validate docker-compose.yml'
                    )

                    echo '[PASS] Docker Compose configuration is valid.'

                    // ----------------------------------------------------------
                    // Phase 3: Infrastructure & Configuration Validation (Non-destructive)
                    // ----------------------------------------------------------

                    if (fileExists('terraform/providers.tf')) {
                        echo 'Validating Terraform Infrastructure code...'
                        sh(
                            script: '''
                                if command -v terraform >/dev/null 2>&1; then
                                    cd terraform && terraform fmt -check -recursive && terraform init -backend=false && terraform validate
                                else
                                    echo "[WARN] Terraform CLI not found on runner node; skipping live terraform validate."
                                fi
                            ''',
                            label: 'Validate Terraform Code'
                        )
                        echo '[PASS] Terraform configuration check completed.'
                    }

                    if (fileExists('ansible/playbooks/site.yml')) {
                        echo 'Validating Ansible Playbook syntax...'
                        sh(
                            script: '''
                                # Note: inventory/hosts.ini.example is used strictly for syntax checking in CI.
                                # Live execution uses the git-ignored inventory/hosts.ini file.
                                if command -v ansible-playbook >/dev/null 2>&1; then
                                    cd ansible && ANSIBLE_ROLES_PATH=roles ansible-playbook -i inventory/hosts.ini.example playbooks/site.yml --syntax-check
                                else
                                    echo "[WARN] Ansible-playbook CLI not found on runner node; skipping live syntax check."
                                fi
                            ''',
                            label: 'Validate Ansible Playbooks'
                        )
                        echo '[PASS] Ansible playbook check completed.'
                    }

                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 3
        // GITLEAKS
        // ======================================================================

        stage('Secret Scan') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 3: DEVSECOPS SECRET SCANNING'
                    echo '============================================================'

                    echo "GitLeaks image: ${env.GITLEAKS_IMAGE}"


                    def gitleaksStatus = sh(

                        script: """
                            docker run --rm \
                                -v "${env.WORKSPACE}:/path:ro" \
                                ${env.GITLEAKS_IMAGE} \
                                detect \
                                --source="/path" \
                                -c="/path/.gitleaks.toml" \
                                --no-git \
                                -v
                        """,

                        returnStatus: true,

                        label:
                            'GitLeaks Secret Scan'
                    )


                    if (gitleaksStatus != 0) {

                        error(
                            'SECURITY GATE FAILURE: ' +
                            'GitLeaks detected a potential secret.'
                        )
                    }


                    echo '[PASS] GitLeaks secret scan completed successfully.'

                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 4
        // DOCKER BUILD
        // ======================================================================

        stage('Docker Build') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 4: DOCKER IMAGE BUILD'
                    echo '============================================================'


                    // ----------------------------------------------------------
                    // Calculate SHA again.
                    //
                    // This is intentional.
                    // It prevents the previous "null" environment variable
                    // problem.
                    // ----------------------------------------------------------

                    def commitSha = sh(
                        script:
                            'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()


                    if (!commitSha) {

                        error(
                            'DOCKER BUILD FAILURE: Git SHA could not be determined.'
                        )
                    }


                    def imageCommit =
                        "${env.APP_NAME}:${commitSha}"

                    def imageBuild =
                        "${env.APP_NAME}:${env.BUILD_NUMBER}"

                    def imageLatest =
                        "${env.APP_NAME}:latest"


                    echo "Git SHA:       ${commitSha}"
                    echo "Primary Image: ${imageCommit}"
                    echo "Build Image:   ${imageBuild}"
                    echo "Latest Image:  ${imageLatest}"


                    // ----------------------------------------------------------
                    // Build Docker image
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker build \
                                -t "${imageCommit}" \
                                -t "${imageBuild}" \
                                -t "${imageLatest}" \
                                .
                        """,

                        label:
                            'Build Nexvion Docker Image'
                    )


                    // ----------------------------------------------------------
                    // Verify image exists
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker image inspect \
                                "${imageCommit}" \
                                > /dev/null
                        """,

                        label:
                            'Verify Docker Image'
                    )


                    echo "[PASS] Docker image built successfully."
                    echo "Built immutable image: ${imageCommit}"


                    // ----------------------------------------------------------
                    // Display images
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker images "${env.APP_NAME}" \
                                --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'
                        """,

                        label:
                            'Display Built Images'
                    )


                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 5
        // TRIVY
        // ======================================================================

        stage('Image Scan') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 5: DEVSECOPS IMAGE VULNERABILITY SCAN'
                    echo '============================================================'


                    // ----------------------------------------------------------
                    // Calculate exact image that was built.
                    // ----------------------------------------------------------

                    def commitSha = sh(
                        script:
                            'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()


                    def imageCommit =
                        "${env.APP_NAME}:${commitSha}"


                    echo "Trivy image: ${env.TRIVY_IMAGE}"
                    echo "Scanning: ${imageCommit}"
                    echo "Severity: ${params.TRIVY_SEVERITY}"


                    // ----------------------------------------------------------
                    // Human-readable Trivy report
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                ${env.TRIVY_IMAGE} \
                                image \
                                --severity "${params.TRIVY_SEVERITY}" \
                                --exit-code 0 \
                                "${imageCommit}"
                        """,

                        label:
                            'Trivy Vulnerability Report'
                    )


                    // ----------------------------------------------------------
                    // Security gate
                    // ----------------------------------------------------------

                    def trivyStatus = sh(

                        script: """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                ${env.TRIVY_IMAGE} \
                                image \
                                --severity "${params.TRIVY_SEVERITY}" \
                                --exit-code 1 \
                                "${imageCommit}"
                        """,

                        returnStatus: true,

                        label:
                            'Trivy Security Gate'
                    )


                    if (trivyStatus != 0) {

                        error(
                            "SECURITY GATE FAILURE: " +
                            "Trivy detected ${params.TRIVY_SEVERITY} " +
                            "vulnerabilities in ${imageCommit}."
                        )
                    }


                    echo '[PASS] Trivy security gate passed.'
                    echo "Scanned immutable image: ${imageCommit}"

                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 6
        // REGISTRY PUSH
        //
        // For your current Phase 2 test:
        //
        // REGISTRY_TYPE    = LOCAL_ONLY
        // PUSH_TO_REGISTRY = false
        //
        // Therefore this stage will be SKIPPED.
        //
        // We leave the stage here for future ECR integration.
        // ======================================================================

        stage('Registry Push') {

            when {

                expression {

                    return (
                        params.PUSH_TO_REGISTRY &&
                        params.REGISTRY_TYPE != 'LOCAL_ONLY'
                    )
                }
            }


            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 6: CONTAINER REGISTRY PUSH'
                    echo '============================================================'


                    if (!params.REGISTRY_URL?.trim()) {

                        error(
                            'REGISTRY_URL must be configured when ' +
                            'registry push is enabled.'
                        )
                    }


                    // ----------------------------------------------------------
                    // Calculate image tags.
                    // ----------------------------------------------------------

                    def commitSha = sh(
                        script:
                            'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()


                    def localCommit =
                        "${env.APP_NAME}:${commitSha}"

                    def localBuild =
                        "${env.APP_NAME}:${env.BUILD_NUMBER}"

                    def localLatest =
                        "${env.APP_NAME}:latest"


                    echo "Registry: ${params.REGISTRY_TYPE}"
                    echo "Registry URL: ${params.REGISTRY_URL}"


                    // ----------------------------------------------------------
                    // AWS ECR
                    //
                    // This is NOT required for current Phase 2 testing.
                    // ----------------------------------------------------------

                    if (params.REGISTRY_TYPE == 'AWS_ECR') {

                        echo 'AWS ECR push selected.'

                        error(
                            'AWS ECR push is intentionally disabled ' +
                            'for the current Phase 2 test. ' +
                            'Enable it only after ECR and credentials ' +
                            'are explicitly configured.'
                        )
                    }


                    // ----------------------------------------------------------
                    // Docker Hub
                    //
                    // This is NOT required for current Phase 2 testing.
                    // ----------------------------------------------------------

                    else if (params.REGISTRY_TYPE == 'DOCKER_HUB') {

                        echo 'Docker Hub push selected.'

                        error(
                            'Docker Hub push is intentionally disabled ' +
                            'for the current Phase 2 test.'
                        )
                    }
                }
            }
        }


        // ======================================================================
        // STAGE 7
        // STAGING DEPLOYMENT
        // ======================================================================

        stage('Staging Deployment') {

            when {

                expression {
                    return params.DEPLOY_STAGING
                }
            }


            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 7: STAGING DEPLOYMENT'
                    echo '============================================================'


                    // ----------------------------------------------------------
                    // Calculate EXACT immutable image that passed Trivy.
                    // ----------------------------------------------------------

                    def commitSha = sh(
                        script:
                            'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()


                    def imageCommit =
                        "${env.APP_NAME}:${commitSha}"


                    echo "Validated image: ${imageCommit}"

                    echo "Compose compatibility tag: ${env.COMPOSE_IMAGE_TAG}"


                    // ----------------------------------------------------------
                    // Verify the scanned image exists before deployment.
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker image inspect \
                                "${imageCommit}" \
                                > /dev/null
                        """,

                        label:
                            'Verify Scanned Image Before Deployment'
                    )


                    // ----------------------------------------------------------
                    // IMPORTANT:
                    //
                    // Current docker-compose.yml uses:
                    //
                    // nexvion-web:v1.0.0
                    //
                    // Therefore temporarily retag the EXACT SHA image that
                    // passed Trivy.
                    //
                    // SHA image:
                    //
                    // nexvion-web:abc1234
                    //
                    // becomes:
                    //
                    // nexvion-web:v1.0.0
                    //
                    // Compose then deploys that exact image.
                    // ----------------------------------------------------------

                    sh(

                        script: """
                            docker tag \
                                "${imageCommit}" \
                                "${env.COMPOSE_IMAGE_TAG}"
                        """,

                        label:
                            'Tag Scanned Image For Compose'
                    )


                    // ----------------------------------------------------------
                    // Deploy
                    // ----------------------------------------------------------

                    sh(

                        script:
                            'docker compose up -d --force-recreate',

                        label:
                            'Deploy Docker Compose Staging'
                    )


                    sleep(
                        time: 5,
                        unit: 'SECONDS'
                    )


                    echo '[PASS] Docker Compose staging deployment completed.'

                    echo '============================================================'
                }
            }
        }


        // ======================================================================
        // STAGE 8
        // HEALTH CHECK
        // ======================================================================

        stage('Health Check') {

            when {

                expression {
                    return params.DEPLOY_STAGING
                }
            }


            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 8: POST-DEPLOYMENT HEALTH VERIFICATION'
                    echo '============================================================'


                    // ----------------------------------------------------------
                    // 1. Container running state
                    // ----------------------------------------------------------

                    def containerState = sh(

                        script:
                            "docker inspect " +
                            "--format='{{.State.Status}}' " +
                            "nexvion-web-container " +
                            "2>/dev/null || echo 'not_found'",

                        returnStdout: true,

                        label:
                            'Check Container State'
                    ).trim()


                    echo "Container State: ${containerState}"


                    if (containerState != 'running') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label:
                                'Dump Container Logs'
                        )


                        error(
                            "HEALTH CHECK FAILURE: " +
                            "Container state is '${containerState}'."
                        )
                    }


                    // ----------------------------------------------------------
                    // 2. Docker health status
                    // ----------------------------------------------------------

                    def healthState = sh(

                        script:
                            "docker inspect " +
                            "--format='{{.State.Health.Status}}' " +
                            "nexvion-web-container " +
                            "2>/dev/null || echo 'unknown'",

                        returnStdout: true,

                        label:
                            'Check Docker Health'
                    ).trim()


                    echo "Docker Health: ${healthState}"


                    if (healthState != 'healthy') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label:
                                'Dump Container Logs'
                        )


                        error(
                            "HEALTH CHECK FAILURE: " +
                            "Docker health status is '${healthState}'."
                        )
                    }


                    // ----------------------------------------------------------
                    // 3. /healthz
                    // ----------------------------------------------------------

                    def healthStatus = sh(

                        script:
                            "curl -s -o /dev/null " +
                            "-w '%{http_code}' " +
                            "${env.HEALTH_CHECK_URL}",

                        returnStdout: true,

                        label:
                            'Check /healthz'
                    ).trim()


                    echo "/healthz HTTP Status: ${healthStatus}"


                    if (healthStatus != '200') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label:
                                'Dump Container Logs'
                        )


                        error(
                            "HEALTH CHECK FAILURE: " +
                            "${env.HEALTH_CHECK_URL} returned " +
                            "HTTP ${healthStatus}."
                        )
                    }


                    // ----------------------------------------------------------
                    // 4. Root /
                    // ----------------------------------------------------------

                    def rootStatus = sh(

                        script:
                            "curl -s -o /dev/null " +
                            "-w '%{http_code}' " +
                            "${env.ROOT_CHECK_URL}",

                        returnStdout: true,

                        label:
                            'Check Root Website'
                    ).trim()


                    echo "Root HTTP Status: ${rootStatus}"


                    if (rootStatus != '200') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label:
                                'Dump Container Logs'
                        )


                        error(
                            "HEALTH CHECK FAILURE: " +
                            "${env.ROOT_CHECK_URL} returned " +
                            "HTTP ${rootStatus}."
                        )
                    }


                    // ----------------------------------------------------------
                    // 5. Application pages
                    // ----------------------------------------------------------

                    def pages = [

                        '/index.html',
                        '/products.html',
                        '/payment.html'

                    ]


                    pages.each { page ->

                        def status = sh(

                            script:
                                "curl -s -o /dev/null " +
                                "-w '%{http_code}' " +
                                "http://localhost:8081${page}",

                            returnStdout: true,

                            label:
                                "Check ${page}"
                        ).trim()


                        echo "${page} HTTP Status: ${status}"


                        if (status != '200') {

                            error(
                                "HEALTH CHECK FAILURE: " +
                                "${page} returned HTTP ${status}."
                            )
                        }
                    }


                    // ----------------------------------------------------------
                    // Final success
                    // ----------------------------------------------------------

                    echo '============================================================'
                    echo '[PASS] ALL PHASE 2 STAGING HEALTH CHECKS PASSED'
                    echo '============================================================'

                    echo "Website: http://localhost:8081"

                    echo "Health: HTTP 200"

                    echo "Deployed Compose Image: ${env.COMPOSE_IMAGE_TAG}"

                    echo 'Security: GitLeaks + Trivy'

                    echo 'Deployment: Docker Compose'

                    echo '============================================================'
                }
            }
        }
    }


    // ==========================================================================
    // POST ACTIONS
    // ==========================================================================

    post {


        // ----------------------------------------------------------------------
        // ALWAYS
        // ----------------------------------------------------------------------

        always {

            echo '============================================================'
            echo 'PIPELINE EXECUTION COMPLETE'
            echo '============================================================'


            // --------------------------------------------------------------
            // Docker diagnostic information.
            // --------------------------------------------------------------

            sh(

                script: '''

                    echo "=============================="
                    echo "Docker Images"
                    echo "=============================="

                    docker images nexvion-web || true


                    echo ""
                    echo "=============================="
                    echo "Nexvion Containers"
                    echo "=============================="

                    docker ps -a \
                        --filter "name=nexvion-web-container" \
                        || true


                    echo ""
                    echo "=============================="
                    echo "Docker Disk Usage"
                    echo "=============================="

                    docker system df || true

                ''',

                label:
                    'Collect Docker Diagnostics'
            )
        }


        // ----------------------------------------------------------------------
        // SUCCESS
        // ----------------------------------------------------------------------

        success {

            echo '============================================================'
            echo 'SUCCESS: NEXVION PHASE 2 PIPELINE PASSED'
            echo '============================================================'

            echo "Build Number: ${env.BUILD_NUMBER}"

            echo 'Checkout:      PASS'

            echo 'Validation:    PASS'

            echo 'GitLeaks:      PASS'

            echo 'Docker Build:  PASS'

            echo 'Trivy:         PASS'

            echo 'Deployment:    PASS'

            echo 'Health Check:  PASS'

            echo '============================================================'
        }


        // ----------------------------------------------------------------------
        // FAILURE
        // ----------------------------------------------------------------------

        failure {

            echo '============================================================'
            echo 'FAILURE: NEXVION PHASE 2 PIPELINE FAILED'
            echo '============================================================'


            sh(

                script: '''

                    echo "Attempting to collect Docker diagnostics..."

                    docker ps -a || true

                    echo ""

                    docker inspect nexvion-web-container 2>/dev/null || true

                    echo ""

                    docker logs --tail=100 nexvion-web-container 2>/dev/null || true

                ''',

                label:
                    'Collect Failure Diagnostics'
            )
        }


        // ----------------------------------------------------------------------
        // CLEANUP
        // ----------------------------------------------------------------------

        cleanup {

            // --------------------------------------------------------------
            // Clean Jenkins workspace after all post actions complete.
            // --------------------------------------------------------------

            cleanWs(
                deleteDirs: true,
                notFailBuild: true
            )
        }
    }
}