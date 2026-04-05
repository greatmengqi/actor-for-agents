package agent.actor

import agent.{AgentOp, Ctx}
import agent.AgentOp.*

// ══════════════════════════════════════════════════════════════
// Actor API
//
// 两种 actor:
//   Actor              — 无状态，纯函数
//   StatefulActor[S]   — 有状态，框架管 load/save
//
// 用户不调 load/save，状态是 receive 的参数和返回值:
//   def receive(msg, state) => (result, newState)
//
// 底层: ref.ask(msg) → ctx.effect(Ask(ref.id, msg))
//       状态 → 框架在首次自动 LoadState，结束时自动 SaveState
// ══════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────
// ActorRef
// ─────────────────────────────────────────────

class ActorRef[M](val id: String):
  def tell(msg: M)(using ctx: ActorContext): Unit =
    ctx.raw.effect(Tell(id, msg.toString))

  def ask(msg: M)(using ctx: ActorContext): String =
    ctx.raw.effect(Ask(id, msg.toString))

  override def toString: String = s"ActorRef($id)"

// ─────────────────────────────────────────────
// ActorContext — 通信 + 输出能力，不含状态
// ─────────────────────────────────────────────

class ActorContext private[actor] (private[actor] val raw: Ctx, val self: ActorRef[?]):
  def actorRef[M](id: String): ActorRef[M] = ActorRef[M](id)

  /** 流式输出 */
  def emit(item: String): Unit = raw.emit(item)

  /** 并行调用多个 actor */
  def askAll(refs: (ActorRef[?], String)*): String =
    raw.parallel(refs.map((ref, msg) => Ask(ref.id, msg.toString))*)

  /** 容错策略 */
  def withPolicy(maxRetries: Int, onExhaust: agent.pb.agent.OnExhaust = agent.pb.agent.OnExhaust.STOP): Unit =
    raw.withPolicy(maxRetries, onExhaust)

// ─────────────────────────────────────────────
// Actor — 无状态
// ─────────────────────────────────────────────

trait Actor:
  def receive(msg: String)(using ctx: ActorContext): String

// ─────────────────────────────────────────────
// StatefulActor[S] — 有状态
//
//   状态是 receive 的参数和返回值
//   框架负责 load 初始状态 + save 新状态
//   用户永远不碰 LoadState/SaveState
// ─────────────────────────────────────────────

trait StatefulActor[S]:
  /** 初始状态 — 首次激活时使用 */
  def initial: S

  /** 状态 → 字符串 (序列化) */
  def encode(state: S): String

  /** 字符串 → 状态 (反序列化) */
  def decode(raw: String): S

  /** 处理消息: (消息, 当前状态) => (结果, 新状态) */
  def receive(msg: String, state: S)(using ctx: ActorContext): (String, S)

// ─────────────────────────────────────────────
// ActorSystem
// ─────────────────────────────────────────────

object ActorSystem:
  private trait ActorEntry:
    def run(ctx: Ctx, msg: String): String

  private var entries = Map.empty[String, ActorEntry]

  def register(name: String, actor: Actor): Unit =
    entries += name -> new ActorEntry:
      def run(ctx: Ctx, msg: String): String =
        given actorCtx: ActorContext = ActorContext(ctx, ActorRef(name))
        actor.receive(msg)

  def register[S](name: String, actor: StatefulActor[S]): Unit =
    entries += name -> new ActorEntry:
      def run(ctx: Ctx, msg: String): String =
        given actorCtx: ActorContext = ActorContext(ctx, ActorRef(name))

        // 框架自动 load 状态
        val raw = ctx.effect(LoadState("__state__"))
        val state = if raw.isEmpty then actor.initial else actor.decode(raw)

        // 用户处理消息
        val (result, newState) = actor.receive(msg, state)

        // 框架自动 save 状态
        ctx.effect(SaveState("__state__", actor.encode(newState)))

        result

  def run(agentType: String, ctx: Ctx, msg: String): Option[String] =
    entries.get(agentType).map(_.run(ctx, msg))
