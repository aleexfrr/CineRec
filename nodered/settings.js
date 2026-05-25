module.exports = {
    uiPort: process.env.PORT || 1880,
    mqttReconnectTime: 15000,
    serialReconnectTime: 15000,
    debugMaxLength: 1000,
    adminAuth: null,
    exportGlobalContextKeys: false,
    externalModules: {
        autoInstall: true,
        palette: {
            allowInstall: true,
        }
    },
    editorTheme: {
        projects: { enabled: false }
    },
    functionExternalModules: true,
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },
    contextStorage: {
        default: { module: "memory" }
    }
}
