import AppKit
import Foundation
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?
    var gzGuiTask: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let screenSize = NSScreen.main?.frame.size ?? CGSize(width: 1280, height: 800)
        let winSize = NSMakeRect(100, 100, screenSize.width * 0.8, screenSize.height * 0.8)
        let style: NSWindow.StyleMask = [.titled, .closable, .miniaturizable, .resizable]
        let win = NSWindow(contentRect: winSize, styleMask: style, backing: .buffered, defer: false)
        win.title = "Gazebo (Metal)"
        win.makeKeyAndOrderFront(nil)
        self.window = win

        launchGazeboGui(in: win)
    }

    func applicationWillTerminate(_ notification: Notification) {
        gzGuiTask?.terminate()
    }

    private func launchGazeboGui(in win: NSWindow) {
        let projectRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        let worldsPath = projectRoot.appendingPathComponent("simulation/gazebo_worlds")
        let modelsPath = projectRoot.appendingPathComponent("simulation/models")
        let resourcePaths = "\(worldsPath.path):\(modelsPath.path)"

        let worldName = ProcessInfo.processInfo.environment["PX4_GZ_WORLD"] ?? "harmonic_heightmap"
        let sdfPath = worldsPath.appendingPathComponent("\(worldName).sdf").path

        // Start Gazebo GUI (Qt uses Metal on macOS)
        let gui = Process()
        gui.launchPath = "/opt/homebrew/bin/gz"
        gui.arguments = ["sim", "-g", "-v", "4", sdfPath]
        var env = ProcessInfo.processInfo.environment
        env["GZ_SIM_RESOURCE_PATH"] = resourcePaths
        gui.environment = env

        let pipeOut = Pipe(); let pipeErr = Pipe()
        gui.standardOutput = pipeOut
        gui.standardError = pipeErr

        pipeOut.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-gui] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        pipeErr.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            if !data.isEmpty, let s = String(data: data, encoding: .utf8) {
                print("[gz-gui:err] \(s.trimmingCharacters(in: .whitespacesAndNewlines))")
            }
        }
        do { try gui.run(); self.gzGuiTask = gui } catch { print("[gz-gui] run error: \(error)") }

        // Hide the placeholder Cocoa window; Gazebo GUI opens its own Qt window
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            win.orderOut(nil)
            NSApp.hide(nil)
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)
app.run()