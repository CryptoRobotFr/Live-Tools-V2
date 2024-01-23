echo Mise à jour du serveur...
sudo apt-get update
echo Installation de pip...
sudo apt install pip -y
touch cronlog.log

echo Installation des packages nécessaires...
cd Live-Tools-V2
pip install -r requirements.txt
git update-index --assume-unchanged secret.py
cd ..
