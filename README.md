# Bot Discord — Rappel de Bump (multi-services)

Ce bot détecte automatiquement quand quelqu'un fait un bump réussi et envoie un rappel
une fois le cooldown terminé. **Disboard** (2h) est déjà préconfiguré. Tu peux ajouter
n'importe quel autre bot de bump (ex : "DL Bump", cooldown 4h) toi-même, sans avoir
besoin de modifier le code.

## 1. Créer le bot sur Discord

1. Va sur https://discord.com/developers/applications
2. Clique sur **New Application**, donne-lui un nom
3. Onglet **Bot** → **Add Bot**
4. Active l'intent **MESSAGE CONTENT INTENT** (obligatoire, sinon le bot ne peut pas lire les messages de Disboard)
5. Copie le **Token** (bouton "Reset Token" si besoin)

## 2. Inviter le bot sur ton serveur

Dans l'onglet **OAuth2 → URL Generator** :
- Scopes : `bot`, `applications.commands`
- Permissions : `Send Messages`, `Read Message History`, `View Channels`, `Mention Everyone` (si tu veux ping un rôle)

Copie l'URL générée et ouvre-la pour inviter le bot.

## 3. Installer et lancer

```bash
cd bump-bot
pip install -r requirements.txt
cp .env.example .env
# Édite .env et mets ton token à la place de "ton_token_ici"
python bot.py
```

## 4. Utilisation

- `/setup salon:#ton-salon role:@TonRole` → configure où et qui ping pour les rappels
- Fais `/bump` normalement dans le salon (Disboard est déjà géré automatiquement, cooldown 2h)
- `/bumpstatus` → voir le temps restant avant le prochain bump possible, pour chaque service
- `/list-bump-services` → voir tous les services configurés sur ton serveur

## 5. Ajouter "DL Bump" (ou tout autre bot de bump)

1. Active le **Mode développeur** dans Discord (Réglages → Avancés → Mode développeur)
2. Fais un clic droit sur le bot "DL Bump" dans la liste des membres → **Copier l'ID**
3. Utilise la commande :
   ```
   /add-bump-service nom:dlbump bump_bot:@DL_Bump mot_cle:"bump effectué" cooldown_heures:4
   ```
   - `bump_bot` : sélectionne directement le bot dans le menu Discord (pas besoin de coller l'ID à la main)
   - `mot_cle` : un mot ou une phrase qui apparaît **dans le message de confirmation** du bot quand le bump réussit (regarde le message qu'il envoie après un bump réussi et copie un bout de texte caractéristique, en minuscules)
   - `cooldown_heures` : `4` dans ton cas

Une fois ajouté, le bot détectera automatiquement les bumps réussis de ce service et enverra un rappel après 4h, dans le même salon que celui configuré avec `/setup`.

## Notes

- Le bot doit avoir la permission de lire les messages dans le salon où `/bump` est utilisé.
- La configuration est sauvegardée dans `config.json`, donc elle survit à un redémarrage.
- Si tu veux héberger ce bot 24/7, regarde des services comme Railway, Render, ou un petit VPS.
