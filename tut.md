# Clonamos repositorio de srsRAN_4G
git clone https://github.com/srsRAN/srsRAN_4G.git

# Cambiamos al directorio del proyecto
cd srsRAN_4G

# Creamos un directorio de construcción
mkdir build

# Cambiamos al directorio de construcción
cd build

# Configuramos el proyecto con CMake
cmake ../

# Compilamos el proyecto
make 

# Realizamos pruebas para verificar la instalación
make test

# Instalamos el proyecto
sudo make install

# Ejecutamos el script de instalación
sudo srsran_install_configs.sh user

