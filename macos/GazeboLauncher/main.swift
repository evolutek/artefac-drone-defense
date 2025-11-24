import AppKit
import Foundation
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?
    var gzGuiTask: Process?
    var gzServerTask: Process?
    var statusLabel: NSTextField?
    var spinner: NSProgressIndicator?
    var gazeboPid: pid_t?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let screenSize = NSScreen.main?.frame.size ?? CGSize(width: 1280, height: 800)
        let winSize = NSMakeRect(100, 100, screenSize.width * 0.8, screenSize.height * 0.8)
        let style: NSWindow.StyleMask = [.titled, .closable, .miniaturizable, .resizable]
        let win = NSWindow(contentRect: winSize, styleMask: style, backing: .buffered, defer: false)
        win.title = "Gazebo (Metal)"
        win.makeKeyAndOrderFront(nil)
        self.window = win
        let label = NSTextField(labelWithString: "Lancement Gazebo (Metal)...")
        label.frame = NSRect(x: 20, y: win.contentLayoutRect.height - 40, width: 400, height: 24)
        win.contentView?.addSubview(label)
        self.statusLabel = label

        let size = win.contentLayoutRect.size
        let sp = NSProgressIndicator(frame: NSRect(x: (size.width - 24)/2, y: (size.height - 24)/2, width: 24, height: 24))
        sp.style = .spinning
        sp.controlSize = .regular
        sp.isIndeterminate = true
        sp.startAnimation(nil)
        win.contentView?.addSubview(sp)
        self.spinner = sp
        let btn = NSButton(title: "Afficher Gazebo", target: self, action: #selector(showGazebo))
        btn.bezelStyle = .rounded
        btn.frame = NSRect(x: (size.width - 160)/2, y: (size.height - 24)/2 - 40, width: 160, height: 28)
        win.contentView?.addSubview(btn)
        NSApp.activate(ignoringOtherApps: true)
        launchGazeboGui(in: win)
    }

    func applicationWillTerminate(_ notification: Notification) {
        gzGuiTask?.terminate()
    }

    private func launchGazeboGui(in win: NSWindow) {
        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        let envRoot = ProcessInfo.processInfo.environment["PROJECT_ROOT"]
        var projectRoot = envRoot != nil ? URL(fileURLWithPath: envRoot!) : cwd
        func resolveRoot(from base: URL) -> URL {
            var candidate = base
            for _ in 0..<3 {
                let simWorlds = candidate.appendingPathComponent("simulation/gazebo_worlds")
                if FileManager.default.fileExists(atPath: simWorlds.path) {
                    return candidate
                }
                candidate = candidate.deletingLastPathComponent()
            }
            return base
        }
        projectRoot = resolveRoot(from: projectRoot)
        let worldsPath = projectRoot.appendingPathComponent("simulation/gazebo_worlds")
        let modelsPath = projectRoot.appendingPathComponent("simulation/models")
        let resourcePaths = "\(worldsPath.path):\(modelsPath.path)"

        let worldName = ProcessInfo.processInfo.environment["PX4_GZ_WORLD"] ?? "harmonic_heightmap"
        let sdfPath = worldsPath.appendingPathComponent("\(worldName).sdf").path
        if !FileManager.default.fileExists(atPath: sdfPath) {
            self.statusLabel?.stringValue = "Monde introuvable: \(worldName)"
            return
        }
        print("[gz-gui] Using project root: \(projectRoot.path)")
        print("[gz-gui] SDF path: \(sdfPath)")

        let server = Process()
        server.launchPath = "/opt/homebrew/bin/gz"
        server.arguments = ["sim", "-s", "-r", "-v", "4", sdfPath]
        var env = ProcessInfo.processInfo.environment
        env["GZ_SIM_RESOURCE_PATH"] = resourcePaths
        server.environment = env

        let srvOut = Pipe(); let srvErr = Pipe()
        server.standardOutput = srvOut
        server.standardError = srvErr

        srvOut.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-srv] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        srvErr.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-srv:err] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        do {
            try server.run(); self.gzServerTask = server
            server.terminationHandler = { [weak self] p in
                DispatchQueue.main.async {
                    self?.statusLabel?.stringValue = "Serveur arrêté"
                    self?.spinner?.isHidden = true
                    self?.window?.makeKeyAndOrderFront(nil)
                }
            }
        } catch {
            self.statusLabel?.stringValue = "Erreur lancement serveur"
            return
        }

        let gui = Process()
        gui.launchPath = "/opt/homebrew/bin/gz"
        gui.arguments = ["sim", "-g", "-v", "4", sdfPath]
        gui.environment = env
        let guiOut = Pipe(); let guiErr = Pipe()
        gui.standardOutput = guiOut
        gui.standardError = guiErr
        guiOut.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-gui] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        guiErr.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-gui:err] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        do {
            try gui.run(); self.gzGuiTask = gui
        } catch {
            self.statusLabel?.stringValue = "Erreur lancement GUI"
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.statusLabel?.stringValue = "Gazebo démarré: \(worldName)"
            self.spinner?.stopAnimation(nil)
            self.spinner?.isHidden = true
            let pid = gui.processIdentifier
            self.gazeboPid = pid
            let ok = self.activateGazebo(pid: pid)
            if !ok { self.window?.makeKeyAndOrderFront(nil) }
        }
    }

    private func activateGazebo(pid: pid_t) -> Bool {
        if let app = NSRunningApplication(processIdentifier: pid) {
            app.activate(options: [.activateAllWindows])
            return true
        }
        let ps = Process()
        ps.launchPath = "/bin/ps"
        ps.arguments = ["-o", "ucomm=", "-p", "\(pid)"]
        let out = Pipe()
        ps.standardOutput = out
        try? ps.run()
        ps.waitUntilExit()
        let data = out.fileHandleForReading.readDataToEndOfFile()
        guard let name = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), !name.isEmpty else { return false }
        let osa = Process()
        osa.launchPath = "/usr/bin/osascript"
        osa.arguments = ["-e", "tell application \"System Events\" to set frontmost of process \"\(name)\" to true"]
        try? osa.run()
        osa.waitUntilExit()
        return osa.terminationStatus == 0
    }

    @objc private func showGazebo() {
        if gzGuiTask == nil || gzGuiTask?.isRunning == false {
            statusLabel?.stringValue = "Relance Gazebo..."
            if let win = self.window { launchGazeboGui(in: win) }
            return
        }
        let apps = NSWorkspace.shared.runningApplications
        if let app = apps.first(where: { ($0.localizedName?.localizedCaseInsensitiveContains("Gazebo") ?? false) || ($0.localizedName?.localizedCaseInsensitiveContains("gz") ?? false) }) {
            app.activate(options: [.activateAllWindows])
            return
        }
        if let pid = gazeboPid { _ = activateGazebo(pid: pid) }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()