IP_SERVIDOR = "192.168.56.10"

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.boot_timeout = 900

  config.vm.provider "virtualbox" do |vb|
    vb.memory = 1024
    vb.cpus = 2
    vb.customize ["modifyvm", :id, "--uartmode1", "disconnected"]
  end

  config.vm.define "servidor" do |s|
    s.vm.hostname = "servidor"
    s.vm.network "private_network", ip: IP_SERVIDOR
    s.vm.provision "shell", inline: <<-SHELL
      set -e
      apt-get update -qq
      apt-get install -y -qq python3-venv
      mkdir -p /opt/tarefas
      cp /vagrant/servidor/servidor.py /vagrant/servidor/requirements.txt /opt/tarefas/
      python3 -m venv /opt/tarefas/venv
      /opt/tarefas/venv/bin/pip install -q -r /opt/tarefas/requirements.txt
      chown -R vagrant:vagrant /opt/tarefas

      cat > /etc/systemd/system/tarefas.service <<'UNIT'
[Unit]
Description=Servidor do Gerenciador de Tarefas
After=network-online.target

[Service]
User=vagrant
WorkingDirectory=/opt/tarefas
ExecStart=/opt/tarefas/venv/bin/python /opt/tarefas/servidor.py --porta 5000 --banco /opt/tarefas/tarefas.db
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

      systemctl daemon-reload
      systemctl enable --now tarefas
      systemctl restart tarefas
    SHELL
  end

  [["cliente1", "192.168.56.11", "Cliente1"],
   ["cliente2", "192.168.56.12", "Cliente2"]].each do |nome_vm, ip, nome_cliente|
    config.vm.define nome_vm do |c|
      c.vm.hostname = nome_vm
      c.vm.network "private_network", ip: ip
      c.vm.provision "shell", inline: <<-SHELL
        set -e
        mkdir -p /opt/tarefas
        cp /vagrant/cliente/cliente.py /opt/tarefas/
        cat > /etc/profile.d/tarefas.sh <<'ENV'
export CLIENTE_NOME=#{nome_cliente}
export SERVIDOR_URL=http://#{IP_SERVIDOR}:5000
alias tarefas='python3 /opt/tarefas/cliente.py'
ENV
      SHELL
    end
  end
end
