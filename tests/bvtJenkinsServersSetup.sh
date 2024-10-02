#!/bin/bash


is_port_available() {
  local port=$1
  (echo >/dev/tcp/localhost/$port) &>/dev/null
  if [ $? -eq 0 ]; then
    return 1 # Port is in use
  else
    return 0 # Port is available
  fi
}


echo "Running Enhanced Basic Verification Test (BVT) for Jenkins versions..."

# Define Jenkins versions to test against
versions=(
  "2.332.3"
  "2.387.1"
)

# Define ports to start Jenkins on
http_port=8080
jnlp_port=50000

# Check and start Jenkins instances
for version in "${versions[@]}"; do
  echo "Starting Jenkins version: $version"

  # Ensure the ports are available
  while ! is_port_available $http_port; do
    http_port=$((http_port + 1))
  done
  while ! is_port_available $jnlp_port; do
    jnlp_port=$((jnlp_port + 1))
  done

  # Start Jenkins container
  container_id=$(docker run -d --name jenkins_$version -p $http_port:8080 -p $jnlp_port:50000 jenkins/jenkins:$version)

  if [ $? -ne 0 ]; then
    echo "Error running Jenkins version: $version"
    exit 1
  fi

  echo "Jenkins $version is running at http://localhost:$http_port"

  # Wait for Jenkins to be fully up
  echo "Waiting for Jenkins to start..."
  sleep 30

  # Check Jenkins is running properly
  if ! curl -s http://localhost:$http_port/login | grep -q "Jenkins"; then
    echo "Error: Jenkins $version is not running properly!"
    docker stop $container_id
    docker rm $container_id
    exit 1
  fi

  echo "Jenkins $version started successfully. Proceeding with job creation."

  # Create and run a Jenkins job using the Jenkins CLI or REST API
  JENKINS_CLI="java -jar jenkins-cli.jar -s http://localhost:$http_port"

  # Download Jenkins CLI
  curl -O http://localhost:$http_port/jnlpJars/jenkins-cli.jar

  # Create a Jenkins job (example: 'test-job')
  job_config="<project><builders><hudson.tasks.Shell><command>echo 'Hello, World!'</command></hudson.tasks.Shell></builders></project>"
  echo $job_config > config.xml

  $JENKINS_CLI create-job test-job < config.xml
  if [ $? -ne 0 ]; then
    echo "Failed to create Jenkins job on Jenkins $version"
    docker stop $container_id
    docker rm $container_id
    exit 1
  fi

  echo "Jenkins job created successfully."

  # Trigger the job
  $JENKINS_CLI build test-job
  if [ $? -ne 0 ]; then
    echo "Failed to trigger Jenkins job on Jenkins $version"
    docker stop $container_id
    docker rm $container_id
    exit 1
  fi

  echo "Jenkins job triggered successfully. Checking the job status."

  # Check the job status
  job_status=$($JENKINS_CLI get-job test-job)
  if [[ $job_status == *"SUCCESS"* ]]; then
    echo "Jenkins job ran successfully."
  else
    echo "Jenkins job failed!"
    docker stop $container_id
    docker rm $container_id
    exit 1
  fi

  # Clean up
  docker stop $container_id
  docker rm $container_id

  echo "Test completed successfully for Jenkins version: $version"

  # Increment ports for the next version
  http_port=$((http_port + 1))
  jnlp_port=$((jnlp_port + 1))
done

echo "All tests passed. You're good to push the code!"
