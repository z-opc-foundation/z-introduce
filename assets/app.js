/* z-desc · 站点交互
   数据来自 window.ZDESC（由 tools/generate.py 从 manifest 登记的全部仓实测生成）。 */
(function () {
  "use strict";

  var D = window.ZDESC;
  if (!D) { console.error("assets/data.js 未加载"); return; }

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var fmt = function (n) { return (n == null ? 0 : n).toLocaleString("en-US"); };
  var layerOf = {};
  D.layers.forEach(function (l) { layerOf[l.id] = l; });

  var LANG_COLOR = {
    Java: "#ff7b54", TypeScript: "#4d9fff", JavaScript: "#ffb454",
    Python: "#7c5cff", Shell: "#35d39a", Vue: "#4dd4e0", SQL: "#e879a6",
    YAML: "#8b93a8", Kotlin: "#a97bff", "C/C++ Header": "#6b7280", Go: "#4dd4e0"
  };

  /* ── Hero ─────────────────────────────────────────── */
  function renderHero() {
    $("#heroDesc").textContent = D.org.tagline + "。" + D.org.desc;
    var s = D.stats;
    var cells = [
      [s.repos, "登记仓库"], [fmt(s.codeFiles), "代码文件"],
      [s.modules, "子模块"], [fmt(s.commits), "Git 提交"]
    ];
    $("#heroStats").innerHTML = cells.map(function (c) {
      return '<div class="hstat"><b>' + c[0] + "</b><span>" + c[1] + "</span></div>";
    }).join("");
  }

  /* ── 分层 ─────────────────────────────────────────── */
  function renderLayers() {
    var order = D.layers, i = 0;
    $("#layerList").innerHTML = order.map(function (l) {
      var chips = l.repos.map(function (r) {
        return '<button class="lchip" data-repo="' + esc(r) + '">' + esc(r) + "</button>";
      }).join("");
      return '<div class="layer layer-' + esc(l.id) + '">' +
        '<div class="layer-name"><b>' + esc(l.name) + "</b><em>" + esc(l.en) + "</em></div>" +
        '<div class="layer-mid"><p>' + esc(l.tagline) + "</p><span>" + esc(l.desc) + "</span></div>" +
        '<div class="layer-repos">' + chips +
        '<span class="lcount">' + l.repos.length + " 仓</span></div></div>";
    }).join("");
  }

  /* ── 依赖 ─────────────────────────────────────────── */
  function renderDeps() {
    var max = Math.max.apply(null, D.depFans.map(function (d) { return d.count; }));
    $("#depFans").innerHTML = D.depFans.map(function (d, i) {
      return '<div class="fan"><span class="fan-name">' + esc(d.name) + "</span>" +
        '<span class="fan-bar"><i style="width:' + Math.round(d.count / max * 100) +
        '%;animation-delay:' + (i * 90) + 'ms"></i></span>' +
        '<span class="fan-n">' + d.count + " 仓</span></div>";
    }).join("");
    $("#zeroDep").innerHTML = D.zeroDep.map(function (z) {
      return '<span class="chip">' + esc(z) + "</span>";
    }).join("");
  }

  /* ── 过滤条 ───────────────────────────────────────── */
  function renderFilters() {
    var all = '<button class="fbtn on" data-layer="all">全部 ' + D.projects.length + "</button>";
    var rest = D.layers.map(function (l) {
      return '<button class="fbtn" data-layer="' + esc(l.id) + '" style="--f:' +
        (LANG_COLOR[l.id] || "var(--accent)") + '">' + esc(l.name) + " " + l.repos.length + "</button>";
    }).join("");
    $("#layerFilters").innerHTML = all + rest;
  }

  /* ── 仓库卡 ───────────────────────────────────────── */
  function badge(p) {
    if (!p.cloned) return '<span class="badge badge-nc">未 clone</span>';
    if (p.published === "central") return '<span class="badge badge-pub">Central</span>';
    if (p.published === "pending") return '<span class="badge badge-none">待发版</span>';
    if (p.published === "meta") return '<span class="badge badge-meta">meta</span>';
    return '<span class="badge badge-priv">不发版</span>';
  }

  function card(p) {
    var c = layerOf[p.layer] ? "var(--l-" + p.layer + ")" : "var(--accent)";
    var sum = p.summary
      ? esc(p.summary)
      : '<span style="color:var(--text-faint)">（本机无 README 摘要，详见 purpose 字段）</span>';
    return '<button class="card layer-' + esc(p.layer) + '" style="--c:' + c + '" data-repo="' +
      esc(p.name) + '">' +
      '<div class="card-top"><span class="card-name">' + esc(p.name) + "</span>" +
      (p.version ? '<span class="card-ver">v' + esc(p.version) + "</span>" : "") + "</div>" +
      '<div class="card-tag">' + esc(p.tagline) + "</div>" +
      '<p class="card-sum">' + sum + "</p>" +
      (p.note ? '<div class="card-note">' + esc(p.note) + "</div>" : "") +
      '<div class="card-foot">' + badge(p) +
      '<span class="card-mods">' + p.modules.length + " 模块</span>" +
      "<span><b>" + fmt(p.codeFiles) + "</b> 文件</span>" +
      (p.commits ? "<span><b>" + fmt(p.commits) + "</b> 提交</span>" : "") +
      "</div></button>";
  }

  var state = { q: "", layer: "all" };

  function match(p) {
    if (state.layer !== "all" && p.layer !== state.layer) return false;
    if (!state.q) return true;
    var hay = [p.name, p.tagline, p.purpose, p.artifactId, p.summary,
      p.modules.join(" "), p.docs.join(" "), p.note].join(" ").toLowerCase();
    return state.q.split(/\s+/).every(function (t) { return hay.indexOf(t) > -1; });
  }

  function renderGrid() {
    var list = D.projects.filter(match);
    $("#repoGrid").innerHTML = list.map(card).join("");
    $("#empty").hidden = list.length > 0;
    var total = D.projects.length;
    $("#resultLine").textContent = list.length === total
      ? "显示全部 " + total + " 个仓库"
      : "匹配 " + list.length + " / " + total + " 个仓库" +
        (state.q ? ' · 关键词「' + state.q + '」' : "") +
        (state.layer !== "all" ? " · " + layerOf[state.layer].name : "");
  }

  /* ── 详情抽屉 ─────────────────────────────────────── */
  function dsec(title, inner) {
    return '<div class="dsec"><h4>' + title + "</h4>" + inner + "</div>";
  }

  function dcell(k, v) {
    return '<div class="dcell"><dt>' + k + "</dt><dd>" + v + "</dd></div>";
  }

  function openDrawer(name) {
    var p = D.projects.filter(function (x) { return x.name === name; })[0];
    if (!p) return;
    var c = "var(--l-" + p.layer + ")";
    var lname = layerOf[p.layer] ? layerOf[p.layer].name : p.layer;

    var h = '<div class="dh" style="--c:' + c + '"><h3 style="color:' + c + '">' +
      esc(p.name) + " " + badge(p) + '</h3><div class="ver">' +
      (p.artifactId ? esc(p.artifactId) : "—") +
      (p.version ? " · v" + esc(p.version) : "") + " · " + esc(lname) + "</div></div>" +
      '<p class="dtag" style="color:' + c + '">' + esc(p.tagline) + "</p>";

    if (p.summary) h += '<p class="dsum">' + esc(p.summary) + "</p>";
    if (p.purpose) h += '<p class="dpurpose">' + esc(p.purpose) + "</p>";
    if (p.note) h += '<div class="dnote">' + esc(p.note) + "</div>";

    var grid = dcell("仓库名", esc(p.name)) +
      dcell("构件坐标", esc(p.artifactId || "—")) +
      dcell("本地版本", p.version ? "v" + esc(p.version) : "—") +
      dcell("发布状态", p.published === "central" ? "已发 Maven Central" :
        p.published === "pending" ? "待发版（未上 Central）" :
        p.published === "meta" ? "meta（不发版）" : "不发版") +
      dcell("可见性", p.private ? "private" : "public") +
      dcell("分层", esc(lname)) +
      dcell("代码文件", fmt(p.codeFiles)) +
      dcell("代码体量", fmt(p.codeKB) + " KB") +
      dcell("子模块", p.modules.length + " 个") +
      dcell("Git 提交", p.commits ? fmt(p.commits) : (p.cloned ? "—" : "未 clone")) +
      dcell("最后提交", p.lastCommit || "—");
    h += dsec("元数据", '<dl class="dgrid">' + grid + "</dl>");

    if (p.modules.length) {
      var shown = p.modules.slice(0, 22);
      h += dsec("模块结构（" + p.modules.length + "）",
        '<div class="mods">' + shown.map(function (m) {
          return '<span class="mod">' + esc(m) + "</span>";
        }).join("") +
        (p.modules.length > shown.length
          ? '<span class="mmore">+' + (p.modules.length - shown.length) + " 更多</span>" : "") +
        "</div>");
    }

    var langs = p.languages || {};
    var keys = Object.keys(langs);
    if (keys.length) {
      var tot = keys.reduce(function (a, k) { return a + langs[k]; }, 0) || 1;
      var bar = keys.map(function (k) {
        return '<i style="width:' + (langs[k] / tot * 100) + '%;background:' +
          (LANG_COLOR[k] || "#66738c") + '"></i>';
      }).join("");
      var legend = keys.slice(0, 6).map(function (k) {
        return '<span><u style="background:' + (LANG_COLOR[k] || "#66738c") + '"></u>' +
          esc(k) + " " + fmt(langs[k]) + "</span>";
      }).join("");
      h += dsec("语言分布", '<div class="langs-bar">' + bar + "</div>" +
        '<div class="langs-legend">' + legend + "</div>");
    }

    var pills = [];
    if (p.docs && p.docs.length) pills.push("文档目录 " + p.docs.join(" / "));
    if (p.frontend && p.frontend.length) pills.push("前端 " + p.frontend.join(" / "));
    if (p.docker) pills.push("含 docker 编排");
    if (p.readmeFile) pills.push("README " + p.readmeFile);
    if (p.language) pills.push("manifest 语言 " + p.language);
    if (pills.length) {
      h += dsec("仓库特征", '<div class="pill-row">' + pills.map(function (x) {
        return '<span class="pill">' + esc(x) + "</span>";
      }).join("") + "</div>");
    }

    if (p.remote) {
      h += dsec("链接", '<div class="dlinks"><a href="' + esc(p.remote) +
        '" target="_blank" rel="noopener noreferrer">GitHub 仓库 ↗</a>' +
        (p.artifactId
          ? '<a href="https://central.sonatype.com/artifact/' + esc(p.artifactId) +
            '" target="_blank" rel="noopener noreferrer">Maven Central ↗</a>'
          : "") + "</div>");
    }

    $("#dBody").innerHTML = h;
    $("#drawer").hidden = false;
    $("#mask").hidden = false;
    document.body.style.overflow = "hidden";
    $("#drawer").scrollTop = 0;
    $("#dClose").focus();
  }

  function closeDrawer() {
    $("#drawer").hidden = true;
    $("#mask").hidden = true;
    document.body.style.overflow = "";
  }

  /* ── 技术栈 ───────────────────────────────────────── */
  function renderStack() {
    var max = Math.max.apply(null, D.languages.map(function (l) { return l.count; }));
    $("#stackChart").innerHTML = D.languages.map(function (l, i) {
      return '<div class="srow"><span class="srow-name">' + esc(l.name) + "</span>" +
        '<span class="srow-bar"><i style="width:' + Math.round(l.count / max * 100) +
        '%;animation-delay:' + (i * 70) + 'ms"></i></span>' +
        '<span class="srow-n">' + fmt(l.count) + " 文件</span></div>";
    }).join("");
  }

  /* ── 关于 ─────────────────────────────────────────── */
  function renderAbout() {
    $("#aboutText").innerHTML = "<p>" + esc(D.org.desc) + "</p><p>" +
      esc(D.org.tagline) + "。组织当前登记 <strong>" + D.stats.repos +
      "</strong> 个仓库，本机已 clone <strong>" + D.stats.cloned +
      "</strong> 个，累计 <strong>" + fmt(D.stats.codeFiles) + "</strong> 个代码文件、" +
      "<strong>" + fmt(D.stats.commits) + "</strong> 次提交。分层之间只允许向下依赖，" +
      "数据面模块彼此不互依，跨中间件的耦合统一收在控制面与组合产品里。</p>" +
      '<p>所有版本、发布状态、依赖计数均来自 <strong>实测</strong>而非声明：' +
      "版本取自各仓 pom 现读，发布状态取自 Maven Central metadata，跨仓依赖取自全仓 pom 扫描。</p>";
    $("#genDate").textContent = D.generated;
    // 静态 HTML 里的 46 只是 JS 未跑时的兜底，真实读数一律取实测数据
    ["browseRepos", "subRepos", "footRepos"].forEach(function (id) {
      var el = $("#" + id);
      if (el) el.textContent = D.stats.repos;
    });
  }

  /* ── 事件 ─────────────────────────────────────────── */
  function bind() {
    var q = $("#q"), timer = null;
    q.addEventListener("input", function () {
      $("#clearQ").hidden = !q.value;
      clearTimeout(timer);
      timer = setTimeout(function () {
        state.q = q.value.trim().toLowerCase();
        renderGrid();
      }, 110);
    });
    $("#clearQ").addEventListener("click", function () {
      q.value = ""; state.q = ""; this.hidden = true; renderGrid(); q.focus();
    });
    $("#layerFilters").addEventListener("click", function (e) {
      var b = e.target.closest(".fbtn"); if (!b) return;
      state.layer = b.dataset.layer;
      [].forEach.call(this.children, function (x) { x.classList.toggle("on", x === b); });
      renderGrid();
      var y = $("#repos").getBoundingClientRect().top + window.scrollY - 66;
      if (window.scrollY > y) window.scrollTo({ top: y, behavior: "smooth" });
    });
    // 卡片点击 + 分层 chip 点击（事件委托）
    document.addEventListener("click", function (e) {
      var cardEl = e.target.closest(".card");
      if (cardEl) { openDrawer(cardEl.dataset.repo); return; }
      var chip = e.target.closest(".lchip");
      if (chip) {
        e.preventDefault();
        var r = chip.dataset.repo;
        var target = document.querySelector('.card[data-repo="' + r + '"]');
        openDrawer(r);
        return target;
      }
    });
    $("#resetBtn").addEventListener("click", function () {
      state.q = ""; state.layer = "all"; $("#q").value = ""; $("#clearQ").hidden = true;
      [].forEach.call($("#layerFilters").children, function (x, i) {
        x.classList.toggle("on", i === 0);
      });
      renderGrid();
    });
    $("#dClose").addEventListener("click", closeDrawer);
    $("#mask").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !$("#drawer").hidden) closeDrawer();
      if (e.key === "/" && document.activeElement !== q) { e.preventDefault(); q.focus(); }
    });

    var nav = $("#nav"), tog = $("#navToggle");
    tog.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      tog.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { nav.classList.remove("open"); tog.setAttribute("aria-expanded", "false"); }
    });

    // 滚动高亮
    var secs = [].slice.call(document.querySelectorAll("main section[id]"));
    var links = {};
    [].forEach.call(nav.querySelectorAll("a"), function (a) {
      links[a.getAttribute("href").slice(1)] = a;
    });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        [].forEach.call(Object.keys(links), function (k) { links[k].classList.remove("on"); });
        if (links[en.target.id]) links[en.target.id].classList.add("on");
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    secs.forEach(function (s) { io.observe(s); });
  }

  renderHero();
  renderLayers();
  renderDeps();
  renderFilters();
  renderGrid();
  renderStack();
  renderAbout();
  bind();
})();
