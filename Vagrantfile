# Vagrantfile, cria e configura as três VMs do projeto.
#
# Com o comando vagrant up, o Vagrant usa o VirtualBox e cria:
#   servidor  (192.168.56.10) -> roda o servidor.py na porta 5000
#   cliente1  (192.168.56.11) -> roda o cliente.py como "Cliente1"
#   cliente2  (192.168.56.12) -> roda o cliente.py como "Cliente2"
#
# como as três ficam numa rede privada, elas conseguem conversar entre si.
# A pasta do projeto aparece dentro de cada VM em /vagrant.

# endereço fixo do servidor, os clientes também usam ele pra poder o encontrar
IP_SERVIDOR = "192.168.56.10"

Vagrant.configure("2") do |config|
  # o sistema que usamos  é Ubuntu 22.04
  config.vm.box = "ubuntu/jammy64"

  # tempo esperado pra cada VM ligar
  # é alto porque em alguns computadores o boot pode ser meio lento
  config.vm.boot_timeout = 900

  # configuração de cada VM, 1 GB de memória e 2 processadores
  # A ultima linha desliga a porta serial, que talvez atrase o boot
  config.vm.provider "virtualbox" do |vb|
    vb.memory = 1024
    vb.cpus = 2
    vb.customize ["modifyvm", :id, "--uartmode1", "disconnected"]
  end

  #VM do servidor 
  # o script so roda uma vez quando a Vm é criada ai
  #  instala o suporte a ambientes virtuais do Python;
  #  copia o servidor para /opt/tarefas e instala o Flask;
  #  cria o serviço tarefas, que liga o servidor sozinho sempre que
  #   a VM é ligada e o reinicia se ele cair por erro.
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
Environment=TAREFAS_DB=/opt/tarefas/tarefas.db
ExecStart=/opt/tarefas/venv/bin/python /opt/tarefas/servidor.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT

      systemctl daemon-reload
      systemctl enable --now tarefas
      systemctl restart tarefas
    SHELL
  end
#VMS dos clientes
  # as duas VMs de cliente são iguais; muda só o nome, o IP e o nome do
  # cliente, por isso são criadas num laço com a lista abaixo
  # O script copia o cliente.py para /opt/tarefas e cria o atalho tarefas,
  # que abre o cliente já com o nome certo e o endereço do servidor.
  [["cliente1", "192.168.56.11", "Cliente1"],
   ["cliente2", "192.168.56.12", "Cliente2"]].each do |nome_vm, ip, nome_cliente|
    config.vm.define nome_vm do |c|
      c.vm.hostname = nome_vm
      c.vm.network "private_network", ip: ip
      c.vm.provision "shell", inline: <<-SHELL
        set -e
        mkdir -p /opt/tarefas
        cp /vagrant/cliente/cliente.py /opt/tarefas/
        echo "alias tarefas='python3 /opt/tarefas/cliente.py #{nome_cliente} http://#{IP_SERVIDOR}:5000'" > /etc/profile.d/tarefas.sh
      SHELL
    end
  end
end
