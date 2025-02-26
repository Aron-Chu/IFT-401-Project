provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "jenkins" {
  ami           = "ami-0b69ea66ff7391e80"
  instance_type = "t2.micro"
  key_name      = var.key_name
  vpc_security_group_ids = [aws_security_group.jenkins_sg.id]

  user_data = <<-EOF
    #!/bin/bash
    sudo apt update -y
    sudo apt install openjdk-11-jdk -y
    wget -q -O - https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo apt-key add -
    sudo sh -c 'echo deb https://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'
    sudo apt update -y
    sudo apt install jenkins -y
    sudo systemctl start jenkins
  EOF

  tags = {
    Name = "JenkinsServer"
  }
}

resource "aws_security_group" "jenkins_sg" {
  name        = "jenkins_sg"
  description = "Allow HTTP (Jenkins) and SSH access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
