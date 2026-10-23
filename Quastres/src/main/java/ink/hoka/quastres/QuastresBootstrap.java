package ink.hoka.quastres;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.suggestion.SuggestionsBuilder;
import io.papermc.paper.command.brigadier.CommandSourceStack;
import io.papermc.paper.command.brigadier.Commands;
import io.papermc.paper.command.brigadier.argument.ArgumentTypes;
import io.papermc.paper.command.brigadier.argument.resolvers.selector.PlayerSelectorArgumentResolver;
import io.papermc.paper.plugin.bootstrap.BootstrapContext;
import io.papermc.paper.plugin.bootstrap.PluginBootstrap;
import io.papermc.paper.plugin.lifecycle.event.types.LifecycleEvents;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

import java.util.List;

/** Paper-плагин: команды через Brigadier. /quastres give <игрок> <id> [кол-во] | list | reload (право quastres.admin). */
@SuppressWarnings("UnstableApiUsage")
public final class QuastresBootstrap implements PluginBootstrap {

    @Override
    public void bootstrap(BootstrapContext ctx) {
        ctx.getLifecycleManager().registerEventHandler(LifecycleEvents.COMMANDS, ev -> {
            LiteralArgumentBuilder<CommandSourceStack> root = Commands.literal("quastres")
                    .requires(src -> src.getSender().hasPermission("quastres.admin"))
                    .executes(c -> { list(c.getSource().getSender()); return 1; })
                    .then(Commands.literal("list").executes(c -> { list(c.getSource().getSender()); return 1; }))
                    .then(Commands.literal("reload").executes(c -> {
                        Quastres q = Quastres.get(); q.reload(); q.msg(c.getSource().getSender(), "reloaded", "count", q.slabs().all().size()); return 1;
                    }))
                    .then(Commands.literal("give")
                            .then(Commands.argument("игрок", ArgumentTypes.player())
                                    .then(Commands.argument("полублок", StringArgumentType.word())
                                            .suggests((c, b) -> suggest(b))
                                            .executes(c -> give(c.getSource().getSender(), c.getArgument("игрок", PlayerSelectorArgumentResolver.class).resolve(c.getSource()), c.getArgument("полублок", String.class), 1))
                                            .then(Commands.argument("кол-во", IntegerArgumentType.integer(1, 64))
                                                    .executes(c -> give(c.getSource().getSender(), c.getArgument("игрок", PlayerSelectorArgumentResolver.class).resolve(c.getSource()), c.getArgument("полублок", String.class), c.getArgument("кол-во", Integer.class)))))));
            ev.registrar().register(root.build(), "Полублоки Quastres", List.of("полублок", "qs"));
        });
    }

    private static java.util.concurrent.CompletableFuture<com.mojang.brigadier.suggestion.Suggestions> suggest(SuggestionsBuilder b) {
        Quastres q = Quastres.get();
        if (q != null) for (String id : q.slabs().all().keySet()) if (id.startsWith(b.getRemainingLowerCase())) b.suggest(id);
        return b.buildFuture();
    }

    private static void list(CommandSender s) {
        Quastres q = Quastres.get();
        q.msg(s, "list", "list", String.join(", ", q.slabs().all().keySet()));
    }

    private static int give(CommandSender s, List<Player> targets, String id, int amount) {
        Quastres q = Quastres.get();
        SlabRegistry.Slab slab = q.slabs().get(id);
        if (slab == null) { q.msg(s, "unknown", "id", id); return 0; }
        for (Player t : targets) {
            for (var rest : t.getInventory().addItem(q.slabs().item(slab, amount)).values()) t.getWorld().dropItemNaturally(t.getLocation(), rest);
            q.msg(s, "given", "count", amount, "name", slab.name(), "player", t.getName());
        }
        return 1;
    }
}
