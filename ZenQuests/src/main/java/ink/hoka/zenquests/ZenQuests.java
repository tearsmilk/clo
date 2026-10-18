package ink.hoka.zenquests;

import ink.hoka.zenquests.menu.QuestMenu;
import ink.hoka.zenquests.model.ObjectiveType;
import ink.hoka.zenquests.util.Text;
import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.command.PluginCommand;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.File;

/** Квесты: ежедневные, еженедельные, сезонные и сюжетные. Меню /квесты, награды — командами консоли. */
public final class ZenQuests extends JavaPlugin {

    private QuestRegistry registry;
    private QuestManager quests;
    private QuestMenu menu;
    private PremiumStore premium;
    private QuestBook book;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        if (!new File(getDataFolder(), "quests.yml").exists()) saveResource("quests.yml", false);

        premium = new PremiumStore(this);
        premium.load();
        registry = new QuestRegistry(this);
        quests = new QuestManager(this);
        menu = new QuestMenu(this);
        loadQuests();

        getServer().getPluginManager().registerEvents(new ProgressListener(this), this);
        getServer().getPluginManager().registerEvents(menu, this);
        book = new QuestBook(this);
        getServer().getPluginManager().registerEvents(book, this);
        ink.hoka.zenquests.hook.TakuFarmersHook.tryRegister(this);
        ink.hoka.zenquests.hook.PapiHook.tryRegister(this);

        PluginCommand cmd = getCommand("quests");
        if (cmd != null) {
            QuestCommand qc = new QuestCommand(this);
            cmd.setExecutor(qc);
            cmd.setTabCompleter(qc);
        }

        // минута игры для PLAYTIME + автосохранение изменённых данных
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (Player p : Bukkit.getOnlinePlayers()) quests.progress(p, ObjectiveType.PLAYTIME, null, 1);
            quests.saveDirty();
        }, 20L * 60, 20L * 60);

        // /reload или поздний запуск — подхватить уже онлайн игроков
        for (Player p : Bukkit.getOnlinePlayers()) quests.refresh(p, false);
    }

    @Override
    public void onDisable() {
        if (quests != null) for (Player p : Bukkit.getOnlinePlayers()) quests.save(p);
    }

    private void loadQuests() {
        registry.load(YamlConfiguration.loadConfiguration(new File(getDataFolder(), "quests.yml")));
    }

    public void reloadAll() {
        reloadConfig();
        premium.load();
        loadQuests();
        for (Player p : Bukkit.getOnlinePlayers()) quests.refresh(p, false);
    }

    public QuestRegistry registry() { return registry; }
    public QuestManager quests() { return quests; }
    public QuestMenu menu() { return menu; }
    public PremiumStore premium() { return premium; }
    public QuestBook book() { return book; }

    public void msg(CommandSender to, String key, Object... kv) {
        String s = getConfig().getString("messages." + key);
        if (s == null || s.isEmpty()) return;
        for (int i = 0; i + 1 < kv.length; i += 2) s = s.replace("{" + kv[i] + "}", String.valueOf(kv[i + 1]));
        String prefix = getConfig().getString("messages.prefix", "");
        for (String line : s.split("\n")) to.sendMessage(Text.parse(prefix + line));
    }
}
