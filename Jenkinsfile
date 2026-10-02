// ==============================================================================
// Nexvion E-Commerce Workload — Phase 2 CI/CD Pipeline
// Target: Single Linux EC2 Jenkins Node
// Deployment: Docker Compose staging on the same EC2
// Security: GitLeaks v8.28.0 + Trivy 0.60.0
//
// PHASE 2 ONLY
// - No Terraform
// - No Ansible
// - No Kubernetes
// - No Helm
// - No ECR required
// - No permanent AWS credentials required
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

        choice(
            name: 'REGISTRY_TYPE',
            choices: ['LOCAL_ONLY', 'AWS_ECR', 'DOCKER_HUB'],
            description: 'Container registry target. Keep LOCAL_ONLY for Phase 2 testing.'
        )

        string(
            name: 'REGISTRY_URL',
            defaultValue: '',
            description: 'Registry URL. Leave empty for LOCAL_ONLY Phase 2 testing.'
        )

        booleanParam(
            name: 'PUSH_TO_REGISTRY',
            defaultValue: false,
            description: 'Push image to a registry. Keep false for Phase 2 local EC2 testing.'
        )

        booleanParam(
            name: 'DEPLOY_STAGING',
            defaultValue: true,
            description: 'Deploy the validated image using Docker Compose.'
        )

        string(
            name: 'TRIVY_SEVERITY',
            defaultValue: 'HIGH,CRITICAL',
            description: 'Vulnerability severity threshold.'
        )
    }

    environment {

        APP_NAME = 'nexvion-web'

        // Phase 2 local testing does not require registry credentials.
        REGISTRY_CREDENTIALS_ID = 'ecr-credentials'

        AWS_REGION = 'ap-south-1'

        HEALTH_CHECK_URL = 'http://localhost:8080/healthz'
        ROOT_CHECK_URL   = 'http://localhost:8080/'

        // Pinned security scanner versions.
        GITLEAKS_IMAGE = 'zricethezav/gitleaks:v8.28.0'
        TRIVY_IMAGE    = 'aquasec/trivy:0.60.0'

        // Node.js container used for syntax validation.
        NODE_IMAGE = 'node:22-alpine'

        // These are populated during Checkout.
        GIT_COMMIT_SHORT = ''
        IMAGE_TAG_COMMIT = ''
        IMAGE_TAG_BUILD  = ''
        IMAGE_TAG_LATEST = ''

        // Temporary Phase 2 Compose compatibility tag.
        //
        // docker-compose.yml currently references:
        // nexvion-web:v1.0.0
        //
        // We retag the already-built/scanned SHA image with this tag
        // immediately before deployment.
        COMPOSE_IMAGE_TAG = 'nexvion-web:v1.0.0'
    }

    stages {

        // ======================================================================
        // STAGE 1 — CHECKOUT
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

                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short=7 HEAD',
                        returnStdout: true
                    ).trim()

                    env.IMAGE_TAG_COMMIT =
                        "${env.APP_NAME}:${env.GIT_COMMIT_SHORT}"

                    env.IMAGE_TAG_BUILD =
                        "${env.APP_NAME}:${env.BUILD_NUMBER}"

                    env.IMAGE_TAG_LATEST =
                        "${env.APP_NAME}:latest"

                    echo "Git Commit SHA: ${env.GIT_COMMIT_SHORT}"
                    echo "Primary Image: ${env.IMAGE_TAG_COMMIT}"
                    echo "Build Image: ${env.IMAGE_TAG_BUILD}"
                    echo "Latest Image: ${env.IMAGE_TAG_LATEST}"
                }
            }
        }

        // ======================================================================
        // STAGE 2 — VALIDATION
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
                    // Uses Dockerized Node.js so Node does not have to be
                    // installed on the Jenkins EC2 host.
                    // ----------------------------------------------------------

                    echo 'Validating JavaScript syntax...'

                    sh(
                        script: """
                            docker run --rm \
                                -v "\${WORKSPACE}:/workspace:ro" \
                                ${env.NODE_IMAGE} \
                                node -c /workspace/script.js
                        """,
                        label: 'Validate script.js'
                    )

                    sh(
                        script: """
                            docker run --rm \
                                -v "\${WORKSPACE}:/workspace:ro" \
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
                        script: 'docker compose config',
                        label: 'Validate docker-compose.yml'
                    )

                    echo '[PASS] Docker Compose configuration is valid.'
                }
            }
        }

        // ======================================================================
        // STAGE 3 — GITLEAKS
        // ======================================================================

        stage('Secret Scan') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 3: DEVSECOPS SECRET SCANNING'
                    echo '============================================================'

                    echo "GitLeaks: ${env.GITLEAKS_IMAGE}"

                    def gitleaksStatus = sh(
                        script: """
                            docker run --rm \
                                -v "\${WORKSPACE}:/path:ro" \
                                ${env.GITLEAKS_IMAGE} \
                                detect \
                                --source="/path" \
                                -c="/path/.gitleaks.toml" \
                                --no-git \
                                -v
                        """,
                        returnStatus: true,
                        label: 'GitLeaks Secret Scan'
                    )

                    if (gitleaksStatus != 0) {

                        error(
                            'SECURITY GATE FAILURE: ' +
                            'GitLeaks detected a potential secret.'
                        )
                    }

                    echo '[PASS] GitLeaks secret scan completed successfully.'
                }
            }
        }

        // ======================================================================
        // STAGE 4 — DOCKER BUILD
        // ======================================================================

        stage('Docker Build') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 4: DOCKER IMAGE BUILD'
                    echo '============================================================'

                    echo "Primary SHA tag: ${env.IMAGE_TAG_COMMIT}"
                    echo "Build tag:       ${env.IMAGE_TAG_BUILD}"
                    echo "Latest tag:      ${env.IMAGE_TAG_LATEST}"

                    sh(
                        script: """
                            docker build \
                                -t "${env.IMAGE_TAG_COMMIT}" \
                                -t "${env.IMAGE_TAG_BUILD}" \
                                -t "${env.IMAGE_TAG_LATEST}" \
                                .
                        """,
                        label: 'Build Nexvion Docker Image'
                    )

                    def imageCheck = sh(
                        script: """
                            docker image inspect \
                                "${env.IMAGE_TAG_COMMIT}" \
                                > /dev/null 2>&1
                        """,
                        returnStatus: true,
                        label: 'Verify Docker Image'
                    )

                    if (imageCheck != 0) {

                        error(
                            "DOCKER BUILD FAILURE: " +
                            "${env.IMAGE_TAG_COMMIT} does not exist."
                        )
                    }

                    echo '[PASS] Docker image built successfully.'

                    sh(
                        script: """
                            docker images "${env.APP_NAME}" \
                                --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}'
                        """,
                        label: 'Display Built Images'
                    )
                }
            }
        }

        // ======================================================================
        // STAGE 5 — TRIVY
        // ======================================================================

        stage('Image Scan') {

            steps {

                script {

                    echo '============================================================'
                    echo 'STAGE 5: DEVSECOPS IMAGE VULNERABILITY SCAN'
                    echo '============================================================'

                    echo "Trivy: ${env.TRIVY_IMAGE}"
                    echo "Scanning: ${env.IMAGE_TAG_COMMIT}"
                    echo "Severity: ${params.TRIVY_SEVERITY}"

                    // ----------------------------------------------------------
                    // Human-readable report
                    // ----------------------------------------------------------

                    sh(
                        script: """
                            docker run --rm \
                                -v /var/run/docker.sock:/var/run/docker.sock \
                                ${env.TRIVY_IMAGE} \
                                image \
                                --severity ${params.TRIVY_SEVERITY} \
                                --exit-code 0 \
                                "${env.IMAGE_TAG_COMMIT}"
                        """,
                        label: 'Trivy Vulnerability Report'
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
                                --severity ${params.TRIVY_SEVERITY} \
                                --exit-code 1 \
                                "${env.IMAGE_TAG_COMMIT}"
                        """,
                        returnStatus: true,
                        label: 'Trivy Security Gate'
                    )

                    if (trivyStatus != 0) {

                        error(
                            "SECURITY GATE FAILURE: " +
                            "Trivy detected ${params.TRIVY_SEVERITY} " +
                            "vulnerabilities."
                        )
                    }

                    echo '[PASS] Trivy security gate passed.'
                }
            }
        }

        // ======================================================================
        // STAGE 6 — OPTIONAL REGISTRY PUSH
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

                    echo "Registry: ${params.REGISTRY_TYPE}"
                    echo "URL: ${params.REGISTRY_URL}"

                    // ----------------------------------------------------------
                    // AWS ECR
                    // ----------------------------------------------------------

                    if (params.REGISTRY_TYPE == 'AWS_ECR') {

                        withCredentials(
                            [
                                usernamePassword(
                                    credentialsId:
                                        env.REGISTRY_CREDENTIALS_ID,

                                    usernameVariable:
                                        'AWS_ACCESS_KEY_ID',

                                    passwordVariable:
                                        'AWS_SECRET_ACCESS_KEY'
                                )
                            ]
                        ) {

                            sh(
                                script: """
                                    aws ecr get-login-password \
                                        --region "${env.AWS_REGION}" \
                                    | docker login \
                                        --username AWS \
                                        --password-stdin \
                                        "${params.REGISTRY_URL}"
                                """,
                                label: 'AWS ECR Login'
                            )

                            def remoteSHA =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:${env.GIT_COMMIT_SHORT}"

                            def remoteBuild =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:${env.BUILD_NUMBER}"

                            def remoteLatest =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:latest"

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_COMMIT} ${remoteSHA}",
                                label: 'Tag ECR SHA'
                            )

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_BUILD} ${remoteBuild}",
                                label: 'Tag ECR Build'
                            )

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_LATEST} ${remoteLatest}",
                                label: 'Tag ECR Latest'
                            )

                            sh(
                                script:
                                    "docker push ${remoteSHA}",
                                label: 'Push ECR SHA'
                            )

                            sh(
                                script:
                                    "docker push ${remoteBuild}",
                                label: 'Push ECR Build'
                            )

                            sh(
                                script:
                                    "docker push ${remoteLatest}",
                                label: 'Push ECR Latest'
                            )
                        }
                    }

                    // ----------------------------------------------------------
                    // Docker Hub
                    // ----------------------------------------------------------

                    else if (params.REGISTRY_TYPE == 'DOCKER_HUB') {

                        withCredentials(
                            [
                                usernamePassword(
                                    credentialsId:
                                        'docker-registry-credentials',

                                    usernameVariable:
                                        'DOCKER_USER',

                                    passwordVariable:
                                        'DOCKER_PASS'
                                )
                            ]
                        ) {

                            sh(
                                script: '''
                                    echo "$DOCKER_PASS" |
                                    docker login \
                                        --username "$DOCKER_USER" \
                                        --password-stdin
                                ''',
                                label: 'Docker Hub Login'
                            )

                            def remoteSHA =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:${env.GIT_COMMIT_SHORT}"

                            def remoteBuild =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:${env.BUILD_NUMBER}"

                            def remoteLatest =
                                "${params.REGISTRY_URL}/${env.APP_NAME}:latest"

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_COMMIT} ${remoteSHA}",
                                label: 'Tag Docker Hub SHA'
                            )

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_BUILD} ${remoteBuild}",
                                label: 'Tag Docker Hub Build'
                            )

                            sh(
                                script:
                                    "docker tag ${env.IMAGE_TAG_LATEST} ${remoteLatest}",
                                label: 'Tag Docker Hub Latest'
                            )

                            sh(
                                script:
                                    "docker push ${remoteSHA}",
                                label: 'Push Docker Hub SHA'
                            )

                            sh(
                                script:
                                    "docker push ${remoteBuild}",
                                label: 'Push Docker Hub Build'
                            )

                            sh(
                                script:
                                    "docker push ${remoteLatest}",
                                label: 'Push Docker Hub Latest'
                            )
                        }
                    }
                }
            }
        }

        // ======================================================================
        // STAGE 7 — STAGING DEPLOYMENT
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

                    echo "Validated image: ${env.IMAGE_TAG_COMMIT}"

                    // ----------------------------------------------------------
                    // IMPORTANT PHASE 2 STEP
                    //
                    // docker-compose.yml currently references:
                    //
                    // nexvion-web:v1.0.0
                    //
                    // Therefore we temporarily retag the EXACT image that
                    // passed Trivy as v1.0.0.
                    //
                    // This guarantees that Compose deploys the image that
                    // Jenkins actually built and scanned.
                    //
                    // This workaround can be removed later when Compose is
                    // converted to use an injected immutable image tag.
                    // ----------------------------------------------------------

                    sh(
                        script: """
                            docker tag \
                                "${env.IMAGE_TAG_COMMIT}" \
                                "${env.COMPOSE_IMAGE_TAG}"
                        """,
                        label: 'Prepare Immutable Image For Compose'
                    )

                    echo "Compose deployment image: ${env.COMPOSE_IMAGE_TAG}"

                    // ----------------------------------------------------------
                    // Deploy
                    // ----------------------------------------------------------

                    sh(
                        script:
                            'docker compose up -d --force-recreate',
                        label: 'Deploy Docker Compose Staging'
                    )

                    sleep(
                        time: 5,
                        unit: 'SECONDS'
                    )

                    echo '[PASS] Docker Compose staging deployment completed.'
                }
            }
        }

        // ======================================================================
        // STAGE 8 — HEALTH CHECK
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
                    // Container running state
                    // ----------------------------------------------------------

                    def containerState = sh(
                        script:
                            "docker inspect --format='{{.State.Status}}' " +
                            "nexvion-web-container " +
                            "2>/dev/null || echo 'not_found'",

                        returnStdout: true,

                        label: 'Check Container State'
                    ).trim()

                    echo "Container State: ${containerState}"

                    if (containerState != 'running') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label: 'Dump Container Logs'
                        )

                        error(
                            "HEALTH CHECK FAILURE: " +
                            "Container state is '${containerState}'."
                        )
                    }

                    // ----------------------------------------------------------
                    // Docker health status
                    // ----------------------------------------------------------

                    def healthState = sh(
                        script:
                            "docker inspect --format='{{.State.Health.Status}}' " +
                            "nexvion-web-container " +
                            "2>/dev/null || echo 'unknown'",

                        returnStdout: true,

                        label: 'Check Docker Health'
                    ).trim()

                    echo "Docker Health: ${healthState}"

                    if (healthState != 'healthy') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label: 'Dump Container Logs'
                        )

                        error(
                            "HEALTH CHECK FAILURE: " +
                            "Docker health status is '${healthState}'."
                        )
                    }

                    // ----------------------------------------------------------
                    // /healthz
                    // ----------------------------------------------------------

                    def healthStatus = sh(
                        script:
                            "curl -s -o /dev/null -w '%{http_code}' " +
                            "${env.HEALTH_CHECK_URL}",

                        returnStdout: true,

                        label: 'Check /healthz'
                    ).trim()

                    echo "/healthz HTTP Status: ${healthStatus}"

                    if (healthStatus != '200') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label: 'Dump Container Logs'
                        )

                        error(
                            "HEALTH CHECK FAILURE: " +
                            "${env.HEALTH_CHECK_URL} returned " +
                            "HTTP ${healthStatus}."
                        )
                    }

                    // ----------------------------------------------------------
                    // /
                    // ----------------------------------------------------------

                    def rootStatus = sh(
                        script:
                            "curl -s -o /dev/null -w '%{http_code}' " +
                            "${env.ROOT_CHECK_URL}",

                        returnStdout: true,

                        label: 'Check Root Website'
                    ).trim()

                    echo "Root HTTP Status: ${rootStatus}"

                    if (rootStatus != '200') {

                        sh(
                            script:
                                'docker compose logs --tail=100',
                            label: 'Dump Container Logs'
                        )

                        error(
                            "HEALTH CHECK FAILURE: " +
                            "${env.ROOT_CHECK_URL} returned " +
                            "HTTP ${rootStatus}."
                        )
                    }

                    // ----------------------------------------------------------
                    // Application pages
                    // ----------------------------------------------------------

                    def pages = [
                        '/index.html',
                        '/products.html',
                        '/payment.html'
                    ]

                    pages.each { page ->

                        def status = sh(
                            script:
                                "curl -s -o /dev/null -w '%{http_code}' " +
                                "http://localhost:8080${page}",

                            returnStdout: true,

                            label: "Check ${page}"
                        ).trim()

                        echo "${page} HTTP Status: ${status}"

                        if (status != '200') {

                            error(
                                "HEALTH CHECK FAILURE: " +
                                "${page} returned HTTP ${status}."
                            )
                        }
                    }

                    echo '============================================================'
                    echo '[PASS] ALL PHASE 2 STAGING HEALTH CHECKS PASSED'
                    echo '============================================================'
                    echo "Deployed Image: ${env.IMAGE_TAG_COMMIT}"
                    echo "Compose Tag:    ${env.COMPOSE_IMAGE_TAG}"
                    echo 'Website:        http://localhost:8080'
                    echo 'Health:         HTTP 200'
                    echo '============================================================'
                }
            }
        }
    }

    // ========================================================================
    // POST ACTIONS
    // ========================================================================

    post {

        always {

            echo '============================================================'
            echo 'PIPELINE EXECUTION COMPLETE'
            echo '============================================================'

            // Show Docker state for troubleshooting.
            sh(
                script: '''
                    echo "Docker Images:"
                    docker images nexvion-web || true

                    echo ""
                    echo "Docker Containers:"
                    docker ps -a --filter "name=nexvion-web-container" || true
                ''',
                label: 'Collect Docker State'
            )

            cleanWs(
                deleteDirs: true,
                notFailBuild: true
            )
        }

        success {

            echo '============================================================'
            echo 'SUCCESS: NEXVION PHASE 2 PIPELINE PASSED'
            echo '============================================================'
            echo "Primary Image: ${env.IMAGE_TAG_COMMIT}"
            echo "Build Number:  ${env.BUILD_NUMBER}"
            echo 'Security:      GitLeaks + Trivy'
            echo 'Deployment:    Docker Compose'
            echo 'Health:        PASSED'
            echo '============================================================'
        }

        failure {

            echo '============================================================'
            echo 'FAILURE: NEXVION PHASE 2 PIPELINE FAILED'
            echo '============================================================'

            sh(
                script: '''
                    echo "Attempting to collect deployment logs..."
                    docker compose logs --tail=100 || true
                ''',
                label: 'Collect Failure Logs'
            )
        }
    }
}