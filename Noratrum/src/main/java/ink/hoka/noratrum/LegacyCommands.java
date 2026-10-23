package ink.hoka.noratrum;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.Suggestions;
import com.mojang.brigadier.suggestion.SuggestionsBuilder;
import io.papermc.paper.command.brigadier.CommandSourceStack;
import io.papermc.paper.command.brigadier.Commands;
import io.papermc.paper.plugin.lifecycle.event.types.LifecycleEvents;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;

/**
 * Команды старого образца (CommandExecutor/TabCompleter из plugin.yml) поверх Brigadier paper-plugin:
 * /имя [что угодно…] → executor.onCommand(sender, cmd, label, args), подсказки → completer.onTabComplete.
 */
@SuppressWarnings("UnstableApiUsage")
public final class LegacyCommands {

    private record Entry(String name, List<String> aliases, CommandExecutor executor, TabCompleter completer) {}

    private final Noratrum plugin;
    private final List<Entry> entries = new ArrayList<>();
    private boolean hooked;

    LegacyCommands(Noratrum plugin) { this.plugin = plugin; }

    void register(String name, List<String> aliases, CommandExecutor executor, TabCompleter completer) {
        entries.add(new Entry(name, aliases, executor, completer));
    }

    /** Вызвать один раз до того, как сервер соберёт дерево команд (из onEnable хоста). */
    void hook() {
        if (hooked) return;
        hooked = true;
        plugin.getLifecycleManager().registerEventHandler(LifecycleEvents.COMMANDS, ev -> {
            for (Entry e : entries) {
                LiteralArgumentBuilder<CommandSourceStack> root = Commands.literal(e.name())
                        .executes(c -> run(e, c, new String[0]))
                        .then(Commands.argument("args", StringArgumentType.greedyString())
                                .suggests((c, b) -> suggest(e, c, b))
                                .executes(c -> run(e, c, split(c.getArgument("args", String.class)))));
                ev.registrar().register(root.build(), e.name(), e.aliases());
            }
        });
    }

    private static String[] split(String s) {
        s = s.strip();
        return s.isEmpty() ? new String[0] : s.split("\\s+");
    }

    private int run(Entry e, CommandContext<CommandSourceStack> c, String[] args) {
        CommandSender sender = c.getSource().getSender();
        String label = c.getInput().split("\\s+", 2)[0];
        if (label.startsWith("/")) label = label.substring(1);
        e.executor().onCommand(sender, fake(e), label, args);
        return 1;
    }

    private CompletableFuture<Suggestions> suggest(Entry e, CommandContext<CommandSourceStack> c, SuggestionsBuilder b) {
        if (e.completer() == null) return b.buildFuture();
        String rem = b.getRemaining();
        String[] parts = rem.split(" ", -1);           // последний элемент — то, что сейчас печатают (может быть пустым)
        List<String> opts;
        try { opts = e.completer().onTabComplete(c.getSource().getSender(), fake(e), e.name(), parts); }
        catch (Throwable t) { opts = null; }
        if (opts == null) return b.buildFuture();
        // Brigadier подсказывает с позиции начала аргумента "args"; смещаем на уже набранные слова
        int offset = rem.lastIndexOf(' ') + 1;
        SuggestionsBuilder sb = b.createOffset(b.getStart() + offset);
        String cur = parts[parts.length - 1].toLowerCase(Locale.ROOT);
        for (String o : opts) if (o.toLowerCase(Locale.ROOT).startsWith(cur)) sb.suggest(o);
        return sb.buildFuture();
    }

    private Command fake(Entry e) {
        return new Command(e.name(), "", "/" + e.name(), e.aliases()) {
            @Override public boolean execute(CommandSender sender, String label, String[] args) { return e.executor().onCommand(sender, this, label, args); }
        };
    }
}
