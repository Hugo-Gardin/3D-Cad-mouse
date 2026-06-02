# Lessons learned

[2026-06-02] | L'ajout de nouveaux axes sans étendre explicitement le format série casse le parsing côté Python | Toujours versionner/étendre le protocole UART et adapter le parseur en même temps
[2026-06-02] | Un bouton GPIO sans `INPUT_PULLUP` donne des états instables selon le câblage | Initialiser explicitement le mode d'entrée du bouton et normaliser la convention appuyé=1
