// Original local launcher. No vendor identity or administrator privileges.
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Principal;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Codex Usage")]
[assembly: AssemblyDescription("Local Codex Usage launcher")]

[DataContract] public class LauncherConfig {
    [DataMember(Name="python")] public string Python;
    [DataMember(Name="engine")] public string Engine;
}
[DataContract] public class ManagerStatus {
    [DataMember(Name="state")] public string State;
    [DataMember(Name="message")] public string Message;
}
public static class Launcher {
    public const string AppId = "Cocombee.CodexUsage";
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)] static extern int SetCurrentProcessExplicitAppUserModelID(string id);
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)] static extern int SHGetPropertyStoreFromParsingName(string path, IntPtr bind, uint flags, ref Guid iid, out IPropertyStore store);
    [StructLayout(LayoutKind.Sequential)] public struct PropertyKey { public Guid Format; public uint Id; }
    [StructLayout(LayoutKind.Explicit, Size=16)] public struct PropVariant {
        [FieldOffset(0)] public ushort Type;
        [FieldOffset(8)] public IntPtr Text;
    }
    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore {
        [PreserveSig] int GetCount(out uint count);
        [PreserveSig] int GetAt(uint index, out PropertyKey key);
        [PreserveSig] int GetValue(ref PropertyKey key, out PropVariant value);
        [PreserveSig] int SetValue(ref PropertyKey key, ref PropVariant value);
        [PreserveSig] int Commit();
    }
    public static T Read<T>(string path) {
        using (var file=File.OpenRead(path)) return (T)new DataContractJsonSerializer(typeof(T)).ReadObject(file);
    }
    public static void Request(string root) {
        string temporary=Path.Combine(root,"launch-request."+Guid.NewGuid().ToString("N")+".pending");
        File.WriteAllText(temporary,"{\"id\":\""+Guid.NewGuid().ToString("N")+"\"}");
        string destination=Path.Combine(root,"launch-request.json");
        if (File.Exists(destination)) File.Replace(temporary,destination,null); else File.Move(temporary,destination);
    }
    public static void Stamp(string path) {
        path=Path.GetFullPath(path);
        Guid iid=typeof(IPropertyStore).GUID;
        IPropertyStore store;
        Marshal.ThrowExceptionForHR(SHGetPropertyStoreFromParsingName(path,IntPtr.Zero,2,ref iid,out store));
        var key=new PropertyKey {Format=new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"),Id=5};
        var value=new PropVariant {Type=31,Text=Marshal.StringToCoTaskMemUni(AppId)};
        try {Marshal.ThrowExceptionForHR(store.SetValue(ref key,ref value));Marshal.ThrowExceptionForHR(store.Commit());}
        finally {Marshal.FreeCoTaskMem(value.Text);Marshal.ReleaseComObject(store);}
    }
    [STAThread] public static void Main(string[] args) {
        string root=Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        try {
            Marshal.ThrowExceptionForHR(SetCurrentProcessExplicitAppUserModelID(AppId));
            if(args.Length==1 && args[0]=="--exit") {File.WriteAllText(Path.Combine(root,"launcher-stop.request"),"stop");return;}
            if (args.Length==2 && args[0]=="--stamp-shortcut") {Stamp(args[1]);return;}
            if (args.Length==1 && args[0]=="--self-test") {
                var config=Read<LauncherConfig>(Path.Combine(root,"launcher-config.json"));
                if (!File.Exists(config.Python) || !File.Exists(Path.Combine(root,config.Engine,"scripts","windows_manager.py"))) throw new Exception("Launcher dependencies missing");
                File.WriteAllText(Path.Combine(root,"launcher-self-test.json"),"{\"app_id\":\""+AppId+"\",\"passed\":true}");return;
            }
            if(args.Length!=0)throw new Exception("Unknown launcher arguments");
            File.Delete(Path.Combine(root,"launcher-stop.request"));
            Request(root);
            bool created;
            using (var single=new Mutex(true,"Local\\CocombeeCodexUsage-"+WindowsIdentity.GetCurrent().User.Value,out created)) {
                if (!created) return;
                Application.EnableVisualStyles();
                Application.Run(new TrayContext(root));
            }
        } catch (Exception error) {
            Environment.ExitCode=1;
            try {File.WriteAllText(Path.Combine(root,"launcher-error.log"),error.ToString());} catch(IOException) {}
            if(args.Length==0)MessageBox.Show(error.Message,"Codex Usage",MessageBoxButtons.OK,MessageBoxIcon.Error);
        }
    }
}
public sealed class TrayContext : ApplicationContext {
    readonly string root;
    readonly NotifyIcon tray;
    readonly Icon icon;
    readonly System.Windows.Forms.Timer timer;
    Process manager;
    string managerEngine;
    bool changingEngine;
    string lastNotice="";
    public TrayContext(string root) {
        this.root=root;
        string iconPath=Path.Combine(root,"CodexUsage.ico");
        icon=File.Exists(iconPath)?new Icon(iconPath):(Icon)SystemIcons.Application.Clone();
        tray=new NotifyIcon {Text="Codex Usage",Icon=icon,Visible=true};
        var menu=new ContextMenuStrip();
        menu.Items.Add("Open Codex Usage",null,(s,e)=>{Launcher.Request(root);if(manager==null||manager.HasExited)StartManager();});
        menu.Items.Add("Exit launcher",null,(s,e)=>ExitThread());
        tray.ContextMenuStrip=menu;
        tray.DoubleClick+=(s,e)=>Launcher.Request(root);
        StartManager();
        timer=new System.Windows.Forms.Timer {Interval=3000};timer.Tick+=(s,e)=>Refresh();timer.Start();
    }
    void StartManager() {
        File.Delete(Path.Combine(root,"manager-stop.request"));
        var config=Launcher.Read<LauncherConfig>(Path.Combine(root,"launcher-config.json"));
        string engine=Path.GetFullPath(Path.Combine(root,config.Engine));
        if(!engine.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Engine escaped installation directory");
        var start=new ProcessStartInfo(config.Python,"-B \""+Path.Combine(engine,"scripts","windows_manager.py")+"\" --root \""+root+"\"") {
            UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=engine
        };
        manager=Process.Start(start);
        managerEngine=config.Engine;changingEngine=false;
    }
    void Refresh() {
        try {
            if(File.Exists(Path.Combine(root,"launcher-stop.request"))) {ExitThread();return;}
            var config=Launcher.Read<LauncherConfig>(Path.Combine(root,"launcher-config.json"));
            if(config.Engine!=managerEngine && !changingEngine) {
                File.WriteAllText(Path.Combine(root,"manager-stop.request"),"refresh");changingEngine=true;
            }
            if(changingEngine && manager.HasExited)StartManager();
            var status=Launcher.Read<ManagerStatus>(Path.Combine(root,"manager-status.json"));
            string notice=status.State+":"+status.Message;
            if(notice!=lastNotice && (status.State=="unsupported-update"||status.State=="failed")) {
                tray.ShowBalloonTip(8000,"Codex Usage",status.Message,ToolTipIcon.Warning);lastNotice=notice;
            }
        } catch(IOException) {} catch(SerializationException) {}
    }
    protected override void ExitThreadCore() {
        timer.Stop();File.WriteAllText(Path.Combine(root,"manager-stop.request"),"stop");tray.Visible=false;tray.Dispose();icon.Dispose();base.ExitThreadCore();
    }
}
