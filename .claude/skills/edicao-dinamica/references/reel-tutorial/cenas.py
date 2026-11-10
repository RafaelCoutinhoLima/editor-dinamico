# Configuração das cenas do Reel tutorial LoopEdu (fonte: fonte/gravacao.mp4, 1362x596).
# piece: ("src", a, b, fixed)  -> trecho da gravação; fixed=True mantém velocidade normal
#        ("freeze", t, dur)     -> congela o quadro t por dur segundos (câmera continua no relógio t..t+dur)
# cam: (tempo_camera, cx, cy, w, h) em coordenadas da gravação; tempo_camera = tempo da fonte
# caps: (tempo_camera, texto)
SCENES = [
 dict(name="materia", line=1, maxspeed=1.5,
      pieces=[("src",101.6,105.8,False)],
      cam=[(101.6,560,315,780,330),(102.6,560,315,780,330),(105.8,500,300,640,270)],
      caps=[(0,"Digite sua matéria")]),
 dict(name="assuntos", line=2,
      pieces=[("src",108.55,109.95,False),("src",111.6,118.6,False)],
      cam=[(108.55,478,340,640,512),(112.3,478,340,640,512),(113.3,980,255,560,400),(118.6,985,250,540,385)],
      caps=[(0,"Receba os assuntos sugeridos"),(112.5,"Ou cole a ementa do professor")]),
 dict(name="periodos", line=3,
      pieces=[("src",193.6,198.2,False)],
      cam=[(193.6,797,180,1000,330),(195.7,797,180,1000,330),(196.5,640,465,700,250),(198.2,640,465,700,250)],
      caps=[(0,"Escolha os períodos do dia"),(196.3,"E os dias da semana")]),
 dict(name="grade", line=4,
      pieces=[("src",210.2,214.6,False)],
      cam=[(210.2,797,255,1000,380),(211.2,797,255,1000,380),(214.6,740,285,760,300)],
      caps=[(0,"Se preferir, monte seu horário")]),
 dict(name="semana", line=5,
      pieces=[("src",340.0,346.0,False)],
      cam=[(340.0,797,330,1050,470),(342.2,797,330,1050,470),(344.6,560,335,720,440),(346.0,555,340,700,430)],
      caps=[(0,"Sua semana personalizada")]),
 dict(name="lupe", line=6,
      pieces=[("src",286.5,288.0,False),("src",300.6,304.75,False)],
      cam=[(286.5,681,298,1362,596),(286.9,681,298,1362,596),(287.9,941,298,842,596),(305.2,941,298,842,596)],
      caps=[(0,"Tire dúvidas com a Lupe")]),
 dict(name="tutor", line=7,
      pieces=[("src",459.0,465.0,False)],
      cam=[(459.0,680,300,800,480),(465.0,680,285,740,440)],
      caps=[(0,"Estude com o tutor de IA")]),
 dict(name="questao", line=8,
      pieces=[("src",470.0,472.9,False)],
      cam=[(470.0,500,315,800,530),(472.9,500,305,800,530)],
      caps=[(0,"Revise com questões")]),
 dict(name="ajuda", line=9,
      pieces=[("src",479.0,483.0,True)],
      cam=[(479.0,1012,200,700,400),(479.48,1012,190,700,400),(479.70,681,298,840,560),(483.0,681,298,810,540)],
      caps=[(0,"Travou? Peça ajuda")]),
 dict(name="correcao", line=10,
      pieces=[("src",485.2,486.6,True),("freeze",486.6,None)],
      cam=[(485.2,500,300,800,520),(485.95,500,300,800,520),(486.5,505,278,760,450),(489.5,505,278,730,432)],
      caps=[(0,"Veja a correção")]),
 dict(name="resumo", line=11,
      pieces=[("src",504.65,507.0,False),("src",523.5,524.28,True),("freeze",524.28,1.4),("src",541.25,542.65,True)],
      cam=[(504.65,500,330,760,480),(507.0,505,340,720,455),(523.5,1030,290,560,470),(525.7,1030,285,540,450),(541.25,490,330,720,420),(542.65,480,340,690,400)],
      caps=[(0,"Veja o resumo da aula"),(520.0,"Revisões já na sua semana"),(539.5,"O mapa do que você estudou")]),
 dict(name="conquistas", line=12,
      pieces=[("src",434.0,436.8,False),("freeze",436.8,1.1),("src",443.25,444.62,True),("freeze",444.62,2.6)],
      cam=[(434.0,800,323,1080,546),(434.8,800,323,1080,546),(436.3,650,255,760,280),(436.8,650,255,745,274),(437.9,650,255,735,270),
           (443.25,800,323,1080,546),(444.62,800,323,1080,546),(445.4,1006,380,420,262),(447.2,1006,380,400,250)],
      caps=[(0,"Acompanhe sua evolução"),(443.2,"Ganhe insígnias estudando")],
      spot=(444.9,(905,276,1105,484))),
]
# remendo do indicador de teclado "abc" do sistema (cobre x604-758, y378-532 entre 98,5 e 108,3 s)
PATCH = dict(t0=98.5, t1=108.3, rect=(598,372,764,538), clean_t=97.0)

# dados pessoais da conta de teste (nome "Theo"): preenchidos com a cor das bordas, linha a linha
HIDE = [
 (286.0, 288.5, (16,516,226,572)),   # nome na barra lateral
 (286.0, 288.5, (278,148,522,196)),  # "Boa noite, Theo"
 (433.9, 437.7, (425,165,640,201)),  # "Theo · Começando" no cartão de nível
 (443.15, 443.62, (425,62,640,104)),
]
